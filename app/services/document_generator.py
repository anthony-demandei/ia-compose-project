"""
Document Generator Service using Gemini AI.
Generates comprehensive technical documentation with minimum 500 lines per stack.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.models.api_models import StackDocumentation
from app.services.ai_factory import get_ai_provider
from app.utils.pii_safe_logging import get_pii_safe_logger
from app.prompts.documentation_prompts import (
    get_frontend_requirements,
    get_backend_requirements,
    get_database_requirements,
    get_devops_requirements,
    get_complete_prompt_template,
    get_expansion_prompt
)

logger = get_pii_safe_logger(__name__)


class DocumentGeneratorService:
    """Service for generating comprehensive technical documentation using Gemini AI."""
    
    def __init__(self):
        """Initialize the document generator service with AI provider."""
        self.ai_provider = get_ai_provider()
        self.min_lines_per_stack = 500  # Minimum lines of code per stack
        self.max_generation_attempts = 3  # Maximum attempts to generate sufficient content
        logger.info("Document Generator Service initialized with Gemini AI (500+ lines/stack)")
    
    async def generate_documents(self, session_data: Dict[str, Any], include_implementation: bool = True) -> List[StackDocumentation]:
        """
        Generate comprehensive technical documentation for all stacks using AI.
        Ensures minimum 500 lines of actual code per stack.
        
        Args:
            session_data: Complete session data including project info and answers
            include_implementation: Whether to include detailed implementation guidance
            
        Returns:
            List of StackDocumentation objects for each technology stack
        """
        logger.info("Generating AI-powered technical documentation (500+ lines per stack)")
        
        # Extract project info
        project_description = session_data.get("project_description", "")
        answers = session_data.get("answers", [])
        project_classification = session_data.get("project_classification", {})
        
        # Build context from answers
        context = self._build_context(project_description, answers, project_classification)
        
        # Generate all documentation with enhanced prompt
        prompt = self._create_enhanced_documentation_prompt(context, include_implementation)
        
        try:
            # First attempt: Generate all stacks at once
            stacks = await self._generate_with_retries(prompt, context)
            
            # Validate and expand if needed
            stacks = await self._ensure_minimum_content(stacks, context)
            
            total_lines = sum(self._count_lines(s.content) for s in stacks)
            logger.info(f"Successfully generated {len(stacks)} stacks with {total_lines} total lines")
            
            return stacks
            
        except Exception as e:
            logger.error(f"Error generating AI documentation: {str(e)}")
            # Generate comprehensive fallback with more content
            return self._generate_enhanced_fallback(context)
    
    async def _generate_with_retries(self, prompt: str, context: Dict[str, Any]) -> List[StackDocumentation]:
        """Generate documentation with retry logic for better results."""
        
        for attempt in range(self.max_generation_attempts):
            try:
                logger.info(f"Generation attempt {attempt + 1}/{self.max_generation_attempts}")
                
                # Use Gemini with increased token limit (1.5-flash as primary now)
                ai_response = await self.ai_provider.generate_json_response(
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert software architect. Generate COMPLETE technical implementations with ACTUAL CODE. Each stack must have 500+ lines of real, executable code."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,  # Higher temperature for more detailed content
                    max_tokens=16000,  # Increased from 8000 to accommodate more content
                    fallback_model="gemini-1.5-pro"  # Use Pro as fallback
                )
                
                # Parse response
                stacks = self._parse_ai_response(ai_response)
                
                # Check if we got sufficient content
                total_content_size = sum(len(s.content) for s in stacks)
                total_lines = sum(self._count_lines(s.content) for s in stacks)
                
                logger.info(f"Attempt {attempt + 1}: Generated {total_content_size} chars, {total_lines} lines")
                
                if total_lines >= (self.min_lines_per_stack * 4):  # 4 stacks
                    return stacks
                
                # If not enough content, modify prompt for next attempt
                prompt = self._enhance_prompt_for_retry(prompt, total_lines)
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                continue
        
        # If all attempts failed, return what we have
        logger.warning("Could not generate minimum content after all attempts")
        return stacks if 'stacks' in locals() else []
    
    async def _ensure_minimum_content(self, stacks: List[StackDocumentation], context: Dict[str, Any]) -> List[StackDocumentation]:
        """Ensure each stack has minimum required content."""
        
        enhanced_stacks = []
        
        for stack in stacks:
            lines = self._count_lines(stack.content)
            
            if lines < self.min_lines_per_stack:
                logger.info(f"Expanding {stack.stack_type}: {lines} -> {self.min_lines_per_stack}+ lines")
                
                # Generate expansion prompt
                expansion_prompt = get_expansion_prompt(
                    stack.stack_type,
                    stack.content,
                    lines
                )
                
                try:
                    # Request additional content
                    expansion_response = await self.ai_provider.generate_response(
                        messages=[
                            {"role": "system", "content": "Generate additional technical code to expand the documentation."},
                            {"role": "user", "content": expansion_prompt}
                        ],
                        temperature=0.8,
                        max_tokens=8000
                    )
                    
                    # Append additional content
                    stack.content += "\n\n" + expansion_response
                    
                except Exception as e:
                    logger.error(f"Failed to expand {stack.stack_type}: {str(e)}")
            
            enhanced_stacks.append(stack)
        
        return enhanced_stacks
    
    def _create_enhanced_documentation_prompt(self, context: Dict[str, Any], include_implementation: bool) -> str:
        """Create enhanced prompt with detailed requirements for each stack."""
        
        # Get the base template
        template = get_complete_prompt_template()
        
        # Build project context
        project_context = f"""
PROJECT DETAILS:
{context['project_description']}

PROJECT TYPE: {context['classification'].get('type', 'system')}
COMPLEXITY: {context['classification'].get('complexity', 'moderate')}
KEY TECHNOLOGIES: {', '.join(context['classification'].get('key_technologies', []))}

REQUIREMENTS:
- PLATFORMS: {', '.join(context['requirements']['platforms']) if context['requirements']['platforms'] else 'Web, Mobile'}
- INTEGRATIONS: {', '.join(context['requirements']['integrations']) if context['requirements']['integrations'] else 'REST APIs, Webhooks'}
- COMPLIANCE: {', '.join(context['requirements']['compliance']) if context['requirements']['compliance'] else 'LGPD, Security Best Practices'}
- PERFORMANCE: {context['requirements']['performance'].get('sla', 'High Availability 99.9%')}

DETAILED REQUIREMENTS FOR EACH STACK:

FRONTEND (500+ lines):
{get_frontend_requirements()}

BACKEND (500+ lines):
{get_backend_requirements()}

DATABASE (500+ lines):
{get_database_requirements()}

DEVOPS (500+ lines):
{get_devops_requirements()}
"""
        
        # Fill the template
        prompt = template.replace("{project_context}", project_context)
        
        return prompt
    
    def _enhance_prompt_for_retry(self, original_prompt: str, current_lines: int) -> str:
        """Enhance prompt for retry attempt to get more content."""
        
        missing_lines = (self.min_lines_per_stack * 4) - current_lines
        
        enhancement = f"""
IMPORTANT: The previous generation only produced {current_lines} lines total.
You MUST generate {missing_lines} MORE lines of ACTUAL CODE.

Requirements:
- DO NOT use placeholders like "// ... more code here"
- DO NOT use comments to describe what should be done
- WRITE the actual, complete, executable code
- Include FULL implementations, not snippets
- Add more files, more functions, more configurations
"""
        
        return original_prompt + enhancement
    
    def _count_lines(self, content: str) -> int:
        """Count actual lines in content."""
        return len(content.split('\n'))
    
    def _build_context(self, project_description: str, answers: List[Dict], classification: Dict) -> Dict[str, Any]:
        """Build context from project data for AI prompt."""
        context = {
            "project_description": project_description,
            "classification": classification,
            "requirements": {
                "platforms": [],
                "integrations": [],
                "compliance": [],
                "performance": {},
                "business_model": {}
            }
        }
        
        # Analyze answers to extract key requirements
        for answer in answers:
            # Handle both dict format and object format
            if hasattr(answer, 'question_code'):
                question_code = answer.question_code
                selected_choices = answer.selected_choices
            else:
                question_code = answer.get("question_code", "")
                selected_choices = answer.get("selected_choices", [])
            
            # Map answers to context
            if any(term in question_code.lower() for term in ["device", "platform", "dispositivo"]):
                context["requirements"]["platforms"].extend(selected_choices)
            elif any(term in question_code.lower() for term in ["integration", "peripheral", "periférico"]):
                context["requirements"]["integrations"].extend(selected_choices)
            elif any(term in question_code.lower() for term in ["compliance", "fiscal", "regulament"]):
                context["requirements"]["compliance"].extend(selected_choices)
            elif any(term in question_code.lower() for term in ["performance", "sla", "desempenho"]):
                context["requirements"]["performance"]["sla"] = selected_choices[0] if selected_choices else "standard"
        
        return context
    
    def _parse_ai_response(self, ai_response: Dict[str, Any]) -> List[StackDocumentation]:
        """Parse AI response into StackDocumentation objects."""
        stacks = []
        
        # Expected structure: {frontend: {...}, backend: {...}, database: {...}, devops: {...}}
        stack_order = ["frontend", "backend", "database", "devops"]
        
        for stack_type in stack_order:
            if stack_type in ai_response:
                stack_data = ai_response[stack_type]
                
                # Create StackDocumentation object
                stack_doc = StackDocumentation(
                    stack_type=stack_type,
                    title=stack_data.get("title", f"{stack_type.title()} Implementation"),
                    content=stack_data.get("content", ""),
                    technologies=stack_data.get("technologies", []),
                    estimated_effort=stack_data.get("estimated_effort", "6-8 weeks")
                )
                stacks.append(stack_doc)
        
        # If AI didn't return all stacks, add missing ones
        if len(stacks) < 4:
            missing_stacks = set(stack_order) - set(s.stack_type for s in stacks)
            for stack_type in missing_stacks:
                stacks.append(self._create_enhanced_default_stack(stack_type))
        
        return stacks
    
    def _create_enhanced_default_stack(self, stack_type: str) -> StackDocumentation:
        """Create an enhanced default stack with more content."""
        
        defaults = {
            "frontend": {
                "title": "Frontend - Complete Implementation",
                "content": self._generate_frontend_template(),
                "technologies": ["Next.js", "React", "TypeScript", "Tailwind CSS", "Zustand"],
                "effort": "6-8 weeks"
            },
            "backend": {
                "title": "Backend - API and Services",
                "content": self._generate_backend_template(),
                "technologies": ["Node.js", "NestJS", "TypeScript", "PostgreSQL", "Redis"],
                "effort": "8-10 weeks"
            },
            "database": {
                "title": "Database - Complete Schema",
                "content": self._generate_database_template(),
                "technologies": ["PostgreSQL", "Redis", "Prisma", "Migrations"],
                "effort": "3-4 weeks"
            },
            "devops": {
                "title": "DevOps - Infrastructure",
                "content": self._generate_devops_template(),
                "technologies": ["Docker", "Kubernetes", "AWS", "GitHub Actions", "Terraform"],
                "effort": "4-5 weeks"
            }
        }
        
        default = defaults.get(stack_type, defaults["backend"])
        
        return StackDocumentation(
            stack_type=stack_type,
            title=default["title"],
            content=default["content"],
            technologies=default["technologies"],
            estimated_effort=default["effort"]
        )
    
    def _generate_enhanced_fallback(self, context: Dict[str, Any]) -> List[StackDocumentation]:
        """Generate enhanced fallback documentation with more content."""
        logger.warning("Using enhanced fallback documentation")
        
        stacks = []
        for stack_type in ["frontend", "backend", "database", "devops"]:
            stacks.append(self._create_enhanced_default_stack(stack_type))
        
        return stacks
    
    def _generate_frontend_template(self) -> str:
        """Generate a comprehensive frontend template."""
        return """# Frontend Implementation

## Project Structure
```
src/
├── components/
│   ├── common/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Layout.tsx
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   └── ProtectedRoute.tsx
│   └── dashboard/
│       ├── Dashboard.tsx
│       └── Stats.tsx
├── pages/
│   ├── index.tsx
│   ├── login.tsx
│   └── dashboard.tsx
├── services/
│   └── api.ts
├── store/
│   └── index.ts
└── types/
    └── index.ts
```

## Components Implementation

### src/components/common/Header.tsx
```typescript
import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuthStore } from '@/store';

export const Header: React.FC = () => {
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  return (
    <header className="bg-white shadow-md">
      <nav className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <Link href="/" className="text-2xl font-bold text-blue-600">
            AppName
          </Link>
          
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Link href="/dashboard" className="text-gray-700 hover:text-blue-600">
                  Dashboard
                </Link>
                <span className="text-gray-600">{user.email}</span>
                <button
                  onClick={handleLogout}
                  className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="text-gray-700 hover:text-blue-600">
                  Login
                </Link>
                <Link
                  href="/register"
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                >
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
};
```

### src/services/api.ts
```typescript
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.api.post('/auth/login', { email, password });
    return response.data;
  }

  async register(data: RegisterData) {
    const response = await this.api.post('/auth/register', data);
    return response.data;
  }

  // User endpoints
  async getCurrentUser() {
    const response = await this.api.get('/users/me');
    return response.data;
  }

  async updateProfile(data: Partial<User>) {
    const response = await this.api.put('/users/me', data);
    return response.data;
  }

  // Data endpoints
  async fetchData(params?: any) {
    const response = await this.api.get('/data', { params });
    return response.data;
  }

  async createItem(data: any) {
    const response = await this.api.post('/items', data);
    return response.data;
  }

  async updateItem(id: string, data: any) {
    const response = await this.api.put(`/items/${id}`, data);
    return response.data;
  }

  async deleteItem(id: string) {
    const response = await this.api.delete(`/items/${id}`);
    return response.data;
  }
}

export default new ApiService();
```

### src/store/index.ts
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/services/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isLoading: false,

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const response = await api.login(email, password);
          set({
            user: response.user,
            token: response.token,
            isLoading: false,
          });
          localStorage.setItem('token', response.token);
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        set({ user: null, token: null });
        localStorage.removeItem('token');
      },

      checkAuth: async () => {
        const token = localStorage.getItem('token');
        if (!token) return;

        set({ isLoading: true });
        try {
          const user = await api.getCurrentUser();
          set({ user, token, isLoading: false });
        } catch {
          set({ user: null, token: null, isLoading: false });
          localStorage.removeItem('token');
        }
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
```

## Configuration Files

### package.json
```json
{
  "name": "frontend-app",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest --watch",
    "test:ci": "jest --ci"
  },
  "dependencies": {
    "next": "14.0.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.2.0",
    "axios": "1.5.0",
    "zustand": "4.4.0",
    "@tanstack/react-query": "5.0.0",
    "react-hook-form": "7.47.0",
    "zod": "3.22.0",
    "tailwindcss": "3.3.0",
    "chart.js": "4.4.0",
    "react-chartjs-2": "5.2.0"
  },
  "devDependencies": {
    "@types/react": "18.2.0",
    "@types/node": "20.0.0",
    "eslint": "8.50.0",
    "eslint-config-next": "14.0.0",
    "jest": "29.7.0",
    "@testing-library/react": "14.0.0",
    "@testing-library/jest-dom": "6.1.0"
  }
}
```

### tailwind.config.js
```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3B82F6',
        secondary: '#10B981',
        accent: '#F59E0B',
      },
    },
  },
  plugins: [],
}
```"""
    
    def _generate_backend_template(self) -> str:
        """Generate a comprehensive backend template."""
        return """# Backend Implementation

## Project Structure
```
src/
├── controllers/
│   ├── auth.controller.ts
│   ├── user.controller.ts
│   └── data.controller.ts
├── services/
│   ├── auth.service.ts
│   ├── user.service.ts
│   └── email.service.ts
├── middleware/
│   ├── auth.middleware.ts
│   ├── validation.middleware.ts
│   └── error.middleware.ts
├── models/
│   ├── user.model.ts
│   └── data.model.ts
├── routes/
│   └── index.ts
├── config/
│   ├── database.ts
│   └── config.ts
└── app.ts
```

## Main Application

### src/app.ts
```typescript
import express, { Application } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { errorMiddleware } from './middleware/error.middleware';
import routes from './routes';
import { connectDatabase } from './config/database';
import config from './config/config';

class App {
  public app: Application;

  constructor() {
    this.app = express();
    this.initializeMiddlewares();
    this.initializeRoutes();
    this.initializeErrorHandling();
    this.connectToDatabase();
  }

  private initializeMiddlewares() {
    this.app.use(helmet());
    this.app.use(cors());
    this.app.use(compression());
    this.app.use(morgan('combined'));
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 100, // limit each IP to 100 requests per windowMs
    });
    this.app.use('/api/', limiter);
  }

  private initializeRoutes() {
    this.app.use('/api', routes);
    this.app.get('/health', (req, res) => {
      res.status(200).json({ status: 'healthy', timestamp: new Date() });
    });
  }

  private initializeErrorHandling() {
    this.app.use(errorMiddleware);
  }

  private async connectToDatabase() {
    try {
      await connectDatabase();
      console.log('Database connected successfully');
    } catch (error) {
      console.error('Database connection failed:', error);
      process.exit(1);
    }
  }

  public listen() {
    this.app.listen(config.port, () => {
      console.log(`Server running on port ${config.port}`);
    });
  }
}

export default App;
```

### src/controllers/auth.controller.ts
```typescript
import { Request, Response, NextFunction } from 'express';
import { AuthService } from '../services/auth.service';
import { validationResult } from 'express-validator';

export class AuthController {
  private authService: AuthService;

  constructor() {
    this.authService = new AuthService();
  }

  public register = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
      }

      const { email, password, name } = req.body;
      const result = await this.authService.register({ email, password, name });

      res.status(201).json({
        success: true,
        message: 'User registered successfully',
        data: result,
      });
    } catch (error) {
      next(error);
    }
  };

  public login = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { email, password } = req.body;
      const result = await this.authService.login(email, password);

      res.status(200).json({
        success: true,
        message: 'Login successful',
        data: result,
      });
    } catch (error) {
      next(error);
    }
  };

  public refreshToken = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { refreshToken } = req.body;
      const result = await this.authService.refreshToken(refreshToken);

      res.status(200).json({
        success: true,
        data: result,
      });
    } catch (error) {
      next(error);
    }
  };

  public logout = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const userId = req.user?.id;
      await this.authService.logout(userId);

      res.status(200).json({
        success: true,
        message: 'Logged out successfully',
      });
    } catch (error) {
      next(error);
    }
  };
}
```

### src/services/auth.service.ts
```typescript
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { User } from '../models/user.model';
import config from '../config/config';
import { AppError } from '../utils/AppError';

export class AuthService {
  public async register(userData: RegisterDTO): Promise<AuthResponse> {
    const existingUser = await User.findOne({ email: userData.email });
    if (existingUser) {
      throw new AppError('User already exists', 400);
    }

    const hashedPassword = await bcrypt.hash(userData.password, 10);
    const user = await User.create({
      ...userData,
      password: hashedPassword,
    });

    const tokens = this.generateTokens(user);
    await this.saveRefreshToken(user.id, tokens.refreshToken);

    return {
      user: this.sanitizeUser(user),
      ...tokens,
    };
  }

  public async login(email: string, password: string): Promise<AuthResponse> {
    const user = await User.findOne({ email }).select('+password');
    if (!user) {
      throw new AppError('Invalid credentials', 401);
    }

    const isPasswordValid = await bcrypt.compare(password, user.password);
    if (!isPasswordValid) {
      throw new AppError('Invalid credentials', 401);
    }

    const tokens = this.generateTokens(user);
    await this.saveRefreshToken(user.id, tokens.refreshToken);

    return {
      user: this.sanitizeUser(user),
      ...tokens,
    };
  }

  private generateTokens(user: any) {
    const accessToken = jwt.sign(
      { id: user.id, email: user.email },
      config.jwt.accessSecret,
      { expiresIn: config.jwt.accessExpiry }
    );

    const refreshToken = jwt.sign(
      { id: user.id },
      config.jwt.refreshSecret,
      { expiresIn: config.jwt.refreshExpiry }
    );

    return { accessToken, refreshToken };
  }

  private sanitizeUser(user: any) {
    const { password, ...sanitized } = user.toObject();
    return sanitized;
  }

  private async saveRefreshToken(userId: string, refreshToken: string) {
    const hashedToken = await bcrypt.hash(refreshToken, 10);
    await User.findByIdAndUpdate(userId, {
      refreshToken: hashedToken,
    });
  }
}
```

## Database Configuration

### src/config/database.ts
```typescript
import mongoose from 'mongoose';
import config from './config';

export const connectDatabase = async (): Promise<void> => {
  try {
    await mongoose.connect(config.database.uri, {
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
    });
    console.log('MongoDB connected successfully');
  } catch (error) {
    console.error('MongoDB connection error:', error);
    throw error;
  }
};
```"""
    
    def _generate_database_template(self) -> str:
        """Generate a comprehensive database template."""
        return """# Database Implementation

## Complete Schema

### schema.sql
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User roles junction table
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(resource, action)
);

-- Role permissions junction table
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Audit log table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Application data tables
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_projects_owner_id ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);

-- Functions and triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Stored procedures
CREATE OR REPLACE FUNCTION authenticate_user(
    p_email VARCHAR,
    p_password_hash VARCHAR
)
RETURNS TABLE (
    user_id UUID,
    user_name VARCHAR,
    user_email VARCHAR,
    roles TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id,
        u.name,
        u.email,
        ARRAY_AGG(r.name) as roles
    FROM users u
    LEFT JOIN user_roles ur ON u.id = ur.user_id
    LEFT JOIN roles r ON ur.role_id = r.id
    WHERE u.email = p_email 
        AND u.password_hash = p_password_hash
        AND u.deleted_at IS NULL
    GROUP BY u.id, u.name, u.email;
END;
$$ LANGUAGE plpgsql;
```

### migrations/001_initial.sql
```sql
-- Migration: Initial Schema
-- Version: 001
-- Date: 2024-01-01

BEGIN;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add more tables...

COMMIT;
```"""
    
    def _generate_devops_template(self) -> str:
        """Generate a comprehensive DevOps template."""
        return """# DevOps Implementation

## Docker Configuration

### Dockerfile.backend
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:4000
    depends_on:
      - backend
    networks:
      - app-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "4000:4000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/appdb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    networks:
      - app-network

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=appdb
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - app-network

volumes:
  postgres-data:

networks:
  app-network:
    driver: bridge
```

## Kubernetes Manifests

### kubernetes/deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
  labels:
    app: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: myapp/backend:latest
        ports:
        - containerPort: 4000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 4000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 4000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## CI/CD Pipeline

### .github/workflows/deploy.yml
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm test
      - run: npm run lint

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t ${{ secrets.DOCKER_REGISTRY }}/app:${{ github.sha }} .
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push ${{ secrets.DOCKER_REGISTRY }}/app:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/backend backend=${{ secrets.DOCKER_REGISTRY }}/app:${{ github.sha }}
          kubectl rollout status deployment/backend
```"""
    
    def calculate_total_effort(self, stacks: List[StackDocumentation]) -> str:
        """Calculate total estimated effort from all stacks."""
        total_weeks = 0
        
        for stack in stacks:
            effort = stack.estimated_effort
            # Extract numeric values from effort string
            numbers = [int(s) for s in effort.split() if s.isdigit()]
            if numbers:
                # Take average if range given
                avg_weeks = sum(numbers) / len(numbers)
                total_weeks += avg_weeks
        
        if total_weeks == 0:
            return "To be determined"
        elif total_weeks <= 20:
            return f"{int(total_weeks)}-{int(total_weeks) + 4} weeks of development"
        else:
            months = int(total_weeks / 4)
            return f"{months}-{months + 2} months of development"
    
    def calculate_timeline(self, stacks: List[StackDocumentation]) -> str:
        """Calculate recommended timeline including testing and deployment."""
        total_weeks = 0
        
        for stack in stacks:
            effort = stack.estimated_effort
            numbers = [int(s) for s in effort.split() if s.isdigit()]
            if numbers:
                avg_weeks = sum(numbers) / len(numbers)
                total_weeks += avg_weeks
        
        # Add 50% buffer for testing, integration, and deployment
        total_weeks = int(total_weeks * 1.5)
        
        if total_weeks == 0:
            return "To be determined"
        elif total_weeks <= 30:
            return f"{int(total_weeks / 4)}-{int(total_weeks / 4) + 1} months including testing and deployment"
        else:
            months = int(total_weeks / 4)
            return f"{months}-{months + 3} months including testing and deployment"