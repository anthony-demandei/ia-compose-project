# ESCOPO COMPLETO FRONTEND - DEMANDEI

## 🎯 VISÃO GERAL

### Stack Tecnológica Definida
- **Framework**: Next.js 15.4.5 + React 19.1.1
- **Build Tool**: Turbopack (nativo do Next.js 15)
- **TypeScript**: 5.9.2
- **Styling**: Tailwind CSS v4.0 + CSS Variables
- **UI Components**: Shadcn UI + Origin UI + Radix UI
- **State Management**: Zustand v5.0.7
- **Forms**: React Hook Form 7.62.0 + Zod
- **Auth**: Better Auth Client
- **HTTP Client**: Axios + TanStack Query 5.84.1
- **Real-time**: Socket.io Client
- **Animations**: Motion for React 12.x (ex-Framer Motion)
- **Mock Data**: Faker.js (pt_BR) + MSW (Mock Service Worker)
- **Testing**: Jest + React Testing Library
- **Deployment**: Vercel + GitHub Actions

### Arquitetura e Conceitos
- **Design Pattern**: Hybrid Command Center (sem sidebar tradicional)
- **Layout**: Mobile-first responsive design
- **Tema**: Light/Dark mode nativo com Pantone 2025 (Mocha Mousse)
- **Performance**: Bundle splitting, lazy loading, image optimization
- **SEO**: Meta tags dinâmicos, structured data, sitemap
- **PWA**: Service Worker, offline support, push notifications

### Compatibilidade React 19
- **React Hook Form 7.62.0**: Totalmente compatível com React 19, funciona junto com server actions
- **Motion for React 12.x**: Suporte alpha para React 19 (rebranding oficial de Framer Motion)
- **Shadcn UI**: Componentes atualizados para Tailwind v4 + React 19, com data-slot attributes
- **TanStack Query 5.84.1**: Compatível com React 19 e Next.js 15.4.5
- **Zustand 5.0.7**: Funciona nativamente com React 19 hooks

## 📁 ESTRUTURA DO PROJETO

```
demandei-web/
├── src/
│   ├── app/                    # App Router (Next.js 15)
│   │   ├── (auth)/            # Rotas de autenticação
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── forgot-password/
│   │   ├── (dashboard)/       # Rotas autenticadas
│   │   │   ├── admin/         # Painel Admin Demandei
│   │   │   ├── company/       # Painel Empresas
│   │   │   ├── freelancer/    # Painel Freelancers
│   │   │   └── layout.tsx
│   │   ├── (public)/          # Rotas públicas
│   │   │   ├── page.tsx       # Landing page
│   │   │   ├── about/
│   │   │   └── pricing/
│   │   ├── api/               # API routes (BFF)
│   │   ├── globals.css
│   │   ├── layout.tsx         # Root layout
│   │   └── providers.tsx      # Context providers
│   ├── components/
│   │   ├── ui/                # Shadcn UI components
│   │   ├── layouts/           # Layout components
│   │   ├── features/          # Feature-specific components
│   │   └── shared/            # Shared components
│   ├── lib/
│   │   ├── api/               # API client & mock
│   │   ├── auth/              # Auth utilities
│   │   ├── utils/             # Helper functions
│   │   └── constants/         # App constants
│   ├── stores/                # Zustand stores
│   ├── hooks/                 # Custom React hooks
│   ├── types/                 # TypeScript types
│   └── styles/                # Global styles
├── public/                    # Static assets
├── tailwind.config.ts
├── next.config.ts
├── package.json
└── README.md
```

## 🎨 DESIGN SYSTEM

### Paleta de Cores
```typescript
// tailwind.config.ts
export const colors = {
  // Cores Principais
  primary: {
    DEFAULT: '#40ca9e',
    hover: '#36b58c',
    light: '#e8f7f3',
    dark: '#2d8f6f'
  },
  secondary: {
    DEFAULT: '#3c3d54',
    light: '#525368',
    dark: '#2a2b3d'
  },
  // Cor Pantone 2025 - Mocha Mousse
  mocha: {
    DEFAULT: '#967C6B',
    light: '#B39686',
    dark: '#7A6355',
    50: '#FAF8F6',
    100: '#F0EBE7',
    500: '#967C6B',
    900: '#4A3E35'
  },
  // Cores Semânticas
  accent: {
    purple: '#844fc1',
    green: '#21bf06',
    pink: '#ff4d6b',
    blue: '#3b82f6',
    orange: '#f97316'
  },
  // Sistema
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
    950: '#030712'
  }
}
```

### Tipografia
```typescript
// Variable Fonts
import { Inter, Roboto_Flex } from 'next/font/google'

export const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap'
})

export const robotoFlex = Roboto_Flex({
  subsets: ['latin'],
  variable: '--font-roboto-flex',
  display: 'swap'
})

// Escala Modular (1.25 ratio)
export const fontSize = {
  xs: '0.75rem',     // 12px
  sm: '0.875rem',    // 14px
  base: '1rem',      // 16px
  lg: '1.25rem',     // 20px
  xl: '1.5625rem',   // 25px
  '2xl': '1.953rem', // 31.25px
  '3xl': '2.441rem', // 39px
  '4xl': '3.052rem', // 48.8px
  '5xl': '3.815rem'  // 61px
}
```

### Configuração Tailwind v4.0
```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Cores customizadas aqui
      },
      fontFamily: {
        sans: ['var(--font-inter)'],
        display: ['var(--font-roboto-flex)']
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-soft': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        }
      },
      screens: {
        'xs': '475px',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio')
  ],
} satisfies Config

export default config
```

## 🏗️ LAYOUT PRINCIPAL - HYBRID COMMAND CENTER

### Conceito de Design
Layout moderno sem sidebar tradicional, focado em produtividade e experiência do usuário com navegação contextual superior.

### Implementação do Layout
```typescript
// src/components/layouts/MainLayout.tsx
'use client'

import { Header } from './Header'
import { Breadcrumb } from './Breadcrumb'
import { StatusBar } from './StatusBar'
import { CommandPalette } from './CommandPalette'
import { NotificationCenter } from './NotificationCenter'

interface MainLayoutProps {
  children: React.ReactNode
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header Superior (60px) */}
      <header className="fixed top-0 z-50 w-full h-[60px] bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between h-full px-4 lg:px-8">
          <Logo />
          <CommandBar />
          <Navigation />
          <div className="flex items-center gap-4">
            <NotificationCenter />
            <ThemeToggle />
            <UserMenu />
          </div>
        </div>
      </header>

      {/* Breadcrumb + Actions (40px) */}
      <div className="fixed top-[60px] z-40 w-full h-[40px] bg-gray-50/80 dark:bg-gray-900/80 backdrop-blur-sm">
        <div className="flex items-center justify-between h-full px-4 lg:px-8">
          <Breadcrumb />
          <ActionButtons />
        </div>
      </div>

      {/* Main Content */}
      <main className="pt-[100px] pb-[30px] min-h-screen">
        <div className="container mx-auto px-4 lg:px-8 max-w-7xl">
          {children}
        </div>
      </main>

      {/* Contextual Footer (30px) */}
      <footer className="fixed bottom-0 z-30 w-full h-[30px] bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <StatusBar />
      </footer>

      {/* Command Palette Modal */}
      <CommandPalette />
    </div>
  )
}
```

### Header Components
```typescript
// src/components/layouts/Header/Logo.tsx
export const Logo = () => (
  <Link href="/" className="flex items-center space-x-2">
    <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
      <span className="text-white font-bold text-sm">D</span>
    </div>
    <span className="text-xl font-bold text-gray-900 dark:text-white">
      Demandei
    </span>
  </Link>
)

// src/components/layouts/Header/CommandBar.tsx
export const CommandBar = () => {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }

    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  return (
    <Button
      variant="outline"
      className="relative h-8 w-full max-w-sm justify-start rounded-[0.5rem] bg-background text-sm font-normal text-muted-foreground shadow-none sm:pr-12 md:w-80"
      onClick={() => setOpen(true)}
    >
      <Search className="mr-2 h-4 w-4" />
      Buscar projetos, freelancers...
      <kbd className="pointer-events-none absolute right-[0.3rem] top-[0.3rem] hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
        <span className="text-xs">⌘</span>K
      </kbd>
    </Button>
  )
}

// src/components/layouts/Header/Navigation.tsx
export const Navigation = () => {
  const { user } = useAuthStore()
  
  const navigationItems = {
    company: [
      { label: 'Dashboard', href: '/company', icon: LayoutDashboard },
      { label: 'Projetos', href: '/company/projects', icon: FolderOpen },
      { label: 'Contratos', href: '/company/contracts', icon: FileText },
      { label: 'Pagamentos', href: '/company/payments', icon: CreditCard }
    ],
    freelancer: [
      { label: 'Dashboard', href: '/freelancer', icon: LayoutDashboard },
      { label: 'Oportunidades', href: '/freelancer/opportunities', icon: Briefcase },
      { label: 'Propostas', href: '/freelancer/proposals', icon: Send },
      { label: 'Contratos', href: '/freelancer/contracts', icon: FileText },
      { label: 'Financeiro', href: '/freelancer/financial', icon: DollarSign }
    ],
    admin: [
      { label: 'Dashboard', href: '/admin', icon: LayoutDashboard },
      { label: 'Usuários', href: '/admin/users', icon: Users },
      { label: 'Projetos', href: '/admin/projects', icon: FolderOpen },
      { label: 'Financeiro', href: '/admin/financial', icon: TrendingUp },
      { label: 'Configurações', href: '/admin/settings', icon: Settings }
    ]
  }

  const items = navigationItems[user?.type?.toLowerCase()] || []

  return (
    <nav className="hidden md:flex items-center space-x-1">
      {items.map((item) => {
        const Icon = item.icon
        return (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-primary hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            <Icon className="mr-2 h-4 w-4" />
            {item.label}
          </Link>
        )
      })}
    </nav>
  )
}
```

### Theme Provider
```typescript
// src/components/providers/ThemeProvider.tsx
'use client'

import { createContext, useContext, useEffect, useState } from 'react'

type Theme = 'dark' | 'light' | 'system'

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

type ThemeProviderState = {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const initialState: ThemeProviderState = {
  theme: 'system',
  setTheme: () => null,
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'demandei-ui-theme',
  ...props
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(storageKey) as Theme) || defaultTheme
  )

  useEffect(() => {
    const root = window.document.documentElement

    root.classList.remove('light', 'dark')

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)')
        .matches
        ? 'dark'
        : 'light'

      root.classList.add(systemTheme)
      return
    }

    root.classList.add(theme)
  }, [theme])

  const value = {
    theme,
    setTheme: (theme: Theme) => {
      localStorage.setItem(storageKey, theme)
      setTheme(theme)
    },
  }

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext)

  if (context === undefined)
    throw new Error('useTheme must be used within a ThemeProvider')

  return context
}
```

## 🧩 SISTEMA DE COMPONENTES UI

### Base Components (Shadcn UI)
```typescript
// src/components/ui/button.tsx
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        success: "bg-accent-green text-white hover:bg-accent-green/90",
        warning: "bg-accent-orange text-white hover:bg-accent-orange/90",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

### Cards e Widgets
```typescript
// src/components/ui/card.tsx
import * as React from "react"
import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border bg-card text-card-foreground shadow-sm",
      className
    )}
    {...props}
  />
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

// src/components/features/dashboard/MetricWidget.tsx
interface MetricWidgetProps {
  title: string
  value: string | number
  change?: number
  trend?: 'up' | 'down' | 'neutral'
  icon: React.ElementType
  description?: string
}

export const MetricWidget = ({ 
  title, 
  value, 
  change, 
  trend = 'neutral',
  icon: Icon,
  description
}: MetricWidgetProps) => {
  return (
    <Card className="relative overflow-hidden transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {change !== undefined && (
          <div className="flex items-center pt-1">
            <TrendIcon trend={trend} />
            <span className={cn(
              "text-xs font-medium ml-1",
              trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600'
            )}>
              {change > 0 ? '+' : ''}{change}%
            </span>
            {description && (
              <span className="text-xs text-muted-foreground ml-2">
                {description}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

const TrendIcon = ({ trend }: { trend: 'up' | 'down' | 'neutral' }) => {
  const icons = {
    up: TrendingUp,
    down: TrendingDown,
    neutral: Minus
  }
  const Icon = icons[trend]
  const colors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-600'
  }
  
  return <Icon className={cn("h-3 w-3", colors[trend])} />
}
```

### Forms e Validação
```typescript
// src/components/ui/form.tsx
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"

// Schema de validação
const projectSchema = z.object({
  title: z.string().min(5, "Título deve ter pelo menos 5 caracteres"),
  description: z.string().min(50, "Descrição deve ter pelo menos 50 caracteres"),
  budgetMin: z.number().min(1000, "Orçamento mínimo deve ser R$ 1.000"),
  budgetMax: z.number().min(1000, "Orçamento máximo deve ser R$ 1.000"),
  deadline: z.date().min(new Date(), "Data deve ser futura"),
  requirements: z.string().min(100, "Requisitos devem ter pelo menos 100 caracteres")
})

type ProjectFormData = z.infer<typeof projectSchema>

// Componente de formulário
export const ProjectForm = ({ onSubmit }: { onSubmit: (data: ProjectFormData) => void }) => {
  const form = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      title: '',
      description: '',
      budgetMin: 5000,
      budgetMax: 50000,
      requirements: ''
    }
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Título do Projeto</FormLabel>
              <FormControl>
                <Input placeholder="Ex: Sistema de E-commerce..." {...field} />
              </FormControl>
              <FormDescription>
                Título claro e descritivo do seu projeto
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Descrição Detalhada</FormLabel>
              <FormControl>
                <Textarea 
                  placeholder="Descreva em detalhes o que você precisa..."
                  className="min-h-[120px]"
                  {...field} 
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="budgetMin"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Orçamento Mínimo (R$)</FormLabel>
                <FormControl>
                  <Input type="number" {...field} onChange={e => field.onChange(+e.target.value)} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="budgetMax"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Orçamento Máximo (R$)</FormLabel>
                <FormControl>
                  <Input type="number" {...field} onChange={e => field.onChange(+e.target.value)} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? 'Criando Projeto...' : 'Criar Projeto'}
        </Button>
      </form>
    </Form>
  )
}
```

## 📱 PAINÉIS ESPECÍFICOS

### 1. Painel Admin Demandei
```typescript
// src/app/(dashboard)/admin/page.tsx
import { Suspense } from 'react'
import { MetricWidget } from '@/components/features/dashboard/MetricWidget'
import { RevenueChart } from '@/components/features/charts/RevenueChart'
import { UserGrowthChart } from '@/components/features/charts/UserGrowthChart'
import { RecentProjectsTable } from '@/components/features/tables/RecentProjectsTable'
import { TopFreelancersTable } from '@/components/features/tables/TopFreelancersTable'
import { DollarSign, Users, FolderOpen, TrendingUp } from 'lucide-react'

export default function AdminDashboard() {
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard Executivo</h1>
          <p className="text-muted-foreground mt-2">
            Visão geral da plataforma e métricas de crescimento
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Exportar Relatório
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Nova Análise
          </Button>
        </div>
      </div>

      {/* Métricas Executivas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Suspense fallback={<MetricWidgetSkeleton />}>
          <MetricWidget 
            title="GMV Mensal" 
            value="R$ 2.5M" 
            change={12.5} 
            trend="up" 
            icon={DollarSign}
            description="vs mês anterior"
          />
        </Suspense>
        <MetricWidget 
          title="Usuários Ativos" 
          value="15.2K" 
          change={8.3} 
          trend="up" 
          icon={Users}
          description="últimos 30 dias"
        />
        <MetricWidget 
          title="Projetos Ativos" 
          value="342" 
          change={-2.1} 
          trend="down" 
          icon={FolderOpen}
          description="em andamento"
        />
        <MetricWidget 
          title="Taxa de Sucesso" 
          value="94.2%" 
          change={1.8} 
          trend="up" 
          icon={TrendingUp}
          description="projetos concluídos"
        />
      </div>

      {/* Gráficos e Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Receita por Mês</CardTitle>
            <CardDescription>
              Evolução da receita nos últimos 12 meses
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Suspense fallback={<ChartSkeleton />}>
              <RevenueChart />
            </Suspense>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Crescimento de Usuários</CardTitle>
            <CardDescription>
              Cadastros de empresas e freelancers
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Suspense fallback={<ChartSkeleton />}>
              <UserGrowthChart />
            </Suspense>
          </CardContent>
        </Card>
      </div>

      {/* Tabelas de Gestão */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Projetos Recentes</CardTitle>
            <CardDescription>
              Últimos projetos criados na plataforma
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RecentProjectsTable />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Freelancers</CardTitle>
            <CardDescription>
              Freelancers com melhor performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TopFreelancersTable />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

### 2. Painel Cliente (Empresas)
```typescript
// src/app/(dashboard)/company/projects/new/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ProjectWizard } from '@/components/features/projects/ProjectWizard'
import { DecompositionPreview } from '@/components/features/projects/DecompositionPreview'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { CheckCircle, Clock, Zap } from 'lucide-react'

export default function NewProjectPage() {
  const [currentStep, setCurrentStep] = useState(1)
  const [projectData, setProjectData] = useState(null)
  const [isDecomposing, setIsDecomposing] = useState(false)
  const router = useRouter()

  const steps = [
    { id: 1, title: 'Detalhes do Projeto', icon: FileText },
    { id: 2, title: 'Requisitos', icon: List },
    { id: 3, title: 'Orçamento e Prazo', icon: Calendar },
    { id: 4, title: 'Revisão Final', icon: CheckCircle }
  ]

  const handleStepComplete = (stepData: any) => {
    setProjectData(prev => ({ ...prev, ...stepData }))
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1)
    } else {
      handleProjectSubmit()
    }
  }

  const handleProjectSubmit = async () => {
    setIsDecomposing(true)
    try {
      const response = await api.projects.create(projectData)
      // Iniciar decomposição por IA
      await api.ai.decomposeProject(response.id)
      router.push(`/company/projects/${response.id}?decomposing=true`)
    } catch (error) {
      console.error('Erro ao criar projeto:', error)
    } finally {
      setIsDecomposing(false)
    }
  }

  if (isDecomposing) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
              <Zap className="w-8 h-8 text-primary animate-pulse" />
            </div>
            <CardTitle>IA Analisando Seu Projeto</CardTitle>
            <CardDescription>
              Nossa inteligência artificial está decompondo seu projeto em micro-tarefas especializadas
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Progress value={65} className="w-full" />
            <div className="text-center text-sm text-muted-foreground">
              Identificando tecnologias e skills necessárias... 65%
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">Nova Demanda</h1>
        <p className="text-muted-foreground mt-2">
          Descreva seu projeto e nossa IA irá decompô-lo em micro-tarefas especializadas
        </p>
      </div>

      {/* Progress Indicator */}
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const Icon = step.icon
          const isActive = step.id === currentStep
          const isCompleted = step.id < currentStep

          return (
            <div key={step.id} className="flex items-center">
              <div className={cn(
                "flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors",
                isActive 
                  ? "border-primary bg-primary text-white" 
                  : isCompleted 
                    ? "border-green-500 bg-green-500 text-white"
                    : "border-gray-300 bg-white text-gray-400"
              )}>
                {isCompleted ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>
              {index < steps.length - 1 && (
                <div className={cn(
                  "w-24 h-px mx-2",
                  step.id < currentStep ? "bg-green-500" : "bg-gray-300"
                )} />
              )}
            </div>
          )
        })}
      </div>

      {/* Wizard Content */}
      <Card>
        <CardContent className="p-8">
          <ProjectWizard 
            currentStep={currentStep}
            onStepComplete={handleStepComplete}
            onBack={() => setCurrentStep(Math.max(1, currentStep - 1))}
            initialData={projectData}
          />
        </CardContent>
      </Card>
    </div>
  )
}
```

### 3. Painel Freelancer
```typescript
// src/app/(dashboard)/freelancer/opportunities/page.tsx
'use client'

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { OpportunityCard } from '@/components/features/opportunities/OpportunityCard'
import { OpportunityFilters } from '@/components/features/opportunities/OpportunityFilters'
import { SearchBar } from '@/components/ui/search-bar'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Filter, Sort, Briefcase, Clock, DollarSign } from 'lucide-react'

export default function OpportunitiesPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedFilters, setSelectedFilters] = useState({
    skills: [],
    budget: { min: 0, max: 100000 },
    complexity: [],
    urgency: []
  })
  const [sortBy, setSortBy] = useState('newest')

  const { data: opportunities, isLoading } = useQuery({
    queryKey: ['opportunities', selectedFilters, sortBy],
    queryFn: () => api.microservices.getRecommended({ 
      filters: selectedFilters,
      sort: sortBy
    })
  })

  const filteredOpportunities = useMemo(() => {
    if (!opportunities) return []
    
    return opportunities.filter(opp => 
      opp.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      opp.description.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [opportunities, searchTerm])

  const stats = {
    total: opportunities?.length || 0,
    matched: filteredOpportunities.length,
    averageBudget: opportunities?.reduce((acc, opp) => acc + opp.budget, 0) / (opportunities?.length || 1) || 0
  }

  if (isLoading) {
    return <OpportunitiesPageSkeleton />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Oportunidades</h1>
          <p className="text-muted-foreground mt-2">
            Encontre projetos que combinam com suas skills
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-sm">
            {stats.matched} oportunidades encontradas
          </Badge>
          <Button variant="outline" size="sm">
            <Bell className="mr-2 h-4 w-4" />
            Criar Alerta
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Oportunidades</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">Disponíveis agora</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Orçamento Médio</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
                .format(stats.averageBudget)}
            </div>
            <p className="text-xs text-muted-foreground">Por projeto</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Match Rate</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">87%</div>
            <p className="text-xs text-muted-foreground">Compatibilidade com skills</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="flex-1">
          <SearchBar 
            placeholder="Buscar por tecnologia, tipo de projeto..."
            value={searchTerm}
            onChange={setSearchTerm}
          />
        </div>
        <div className="flex items-center gap-2">
          <OpportunityFilters 
            filters={selectedFilters}
            onChange={setSelectedFilters}
          />
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-48">
              <Sort className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Ordenar por" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">Mais Recentes</SelectItem>
              <SelectItem value="budget-high">Maior Orçamento</SelectItem>
              <SelectItem value="budget-low">Menor Orçamento</SelectItem>
              <SelectItem value="deadline">Prazo Próximo</SelectItem>
              <SelectItem value="compatibility">Mais Compatível</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Opportunities Tabs */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">Todas ({stats.matched})</TabsTrigger>
          <TabsTrigger value="recommended">Recomendadas (12)</TabsTrigger>
          <TabsTrigger value="urgent">Urgentes (3)</TabsTrigger>
          <TabsTrigger value="high-budget">Alto Orçamento (8)</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {/* Opportunities Grid */}
          <div className="grid gap-6">
            {filteredOpportunities.map((opportunity) => (
              <OpportunityCard
                key={opportunity.id}
                opportunity={opportunity}
                onApply={(id) => router.push(`/freelancer/proposals/new?microservice=${id}`)}
                onSave={(id) => console.log('Salvando oportunidade', id)}
                onShare={(id) => console.log('Compartilhando oportunidade', id)}
              />
            ))}
          </div>

          {filteredOpportunities.length === 0 && (
            <Card className="text-center py-12">
              <CardContent>
                <Briefcase className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">Nenhuma oportunidade encontrada</h3>
                <p className="text-muted-foreground mb-4">
                  Tente ajustar seus filtros ou atualizar suas skills no perfil
                </p>
                <div className="flex gap-2 justify-center">
                  <Button variant="outline" onClick={() => setSelectedFilters({})}>
                    Limpar Filtros
                  </Button>
                  <Button onClick={() => router.push('/freelancer/profile')}>
                    Atualizar Perfil
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

## 🔄 GERENCIAMENTO DE ESTADO

### Zustand Stores
```typescript
// src/stores/auth.store.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  type: 'COMPANY' | 'FREELANCER' | 'ADMIN'
  profile: any
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  
  // Actions
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  updateProfile: (data: any) => Promise<void>
  refreshToken: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true })
        try {
          const response = await api.auth.signIn({ email, password })
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false
          })
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: () => {
        api.auth.signOut()
        set({
          user: null,
          token: null,
          isAuthenticated: false
        })
      },

      updateProfile: async (data: any) => {
        const response = await api.users.updateProfile(data)
        set(state => ({
          user: state.user ? { ...state.user, profile: response } : null
        }))
      },

      refreshToken: async () => {
        try {
          const response = await api.auth.refresh()
          set({ token: response.access_token })
        } catch (error) {
          // Token inválido, fazer logout
          get().logout()
          throw error
        }
      }
    }),
    {
      name: 'demandei-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)

// src/stores/ui.store.ts
interface UIState {
  theme: 'light' | 'dark' | 'system'
  commandPaletteOpen: boolean
  notificationsOpen: boolean
  sidebarOpen: boolean
  
  // Actions
  toggleTheme: () => void
  openCommandPalette: () => void
  closeCommandPalette: () => void
  toggleNotifications: () => void
  toggleSidebar: () => void
}

export const useUIStore = create<UIState>((set) => ({
  theme: 'system',
  commandPaletteOpen: false,
  notificationsOpen: false,
  sidebarOpen: false,

  toggleTheme: () => set((state) => ({
    theme: state.theme === 'light' ? 'dark' : state.theme === 'dark' ? 'system' : 'light'
  })),

  openCommandPalette: () => set({ commandPaletteOpen: true }),
  closeCommandPalette: () => set({ commandPaletteOpen: false }),
  toggleNotifications: () => set(state => ({ notificationsOpen: !state.notificationsOpen })),
  toggleSidebar: () => set(state => ({ sidebarOpen: !state.sidebarOpen }))
}))
```

### React Query Setup
```typescript
// src/lib/query-client.ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutos
      cacheTime: 10 * 60 * 1000, // 10 minutos
      retry: (failureCount, error: any) => {
        if (error?.status === 401) return false
        return failureCount < 3
      }
    },
    mutations: {
      retry: false
    }
  }
})

// src/providers/QueryProvider.tsx
'use client'

import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from '@/lib/query-client'

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

## 🎭 SISTEMA DE MOCK PARA DESENVOLVIMENTO

### Mock Service Worker (MSW)
```typescript
// src/lib/api/mock/handlers.ts
import { http, HttpResponse } from 'msw'
import { faker } from '@faker-js/faker/locale/pt_BR'

faker.seed(123) // Para dados consistentes

export const handlers = [
  // Auth handlers
  http.post('/api/v1/auth/sign-in/email', async ({ request }) => {
    const { email, password } = await request.json()
    
    await new Promise(resolve => setTimeout(resolve, 800)) // Simular latência
    
    if (email === 'admin@demandei.com') {
      return HttpResponse.json({
        user: {
          id: '1',
          email: 'admin@demandei.com',
          type: 'ADMIN',
          profile: { name: 'Administrador' }
        },
        access_token: faker.string.alphanumeric(40)
      })
    }
    
    if (email === 'empresa@teste.com') {
      return HttpResponse.json({
        user: {
          id: '2',
          email: 'empresa@teste.com',
          type: 'COMPANY',
          profile: {
            companyName: 'Tech Solutions Ltda',
            cnpj: '12.345.678/0001-90'
          }
        },
        access_token: faker.string.alphanumeric(40)
      })
    }

    return new HttpResponse(null, { status: 401 })
  }),

  // Projects handlers
  http.get('/api/v1/projects', ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const limit = parseInt(url.searchParams.get('limit') || '20')
    
    const projects = Array.from({ length: 50 }, (_, i) => ({
      id: faker.string.uuid(),
      title: faker.company.catchPhrase(),
      description: faker.lorem.paragraphs(2),
      budget: faker.number.int({ min: 5000, max: 100000 }),
      deadline: faker.date.future().toISOString(),
      status: faker.helpers.arrayElement(['DRAFT', 'PUBLISHED', 'IN_PROGRESS', 'COMPLETED']),
      createdAt: faker.date.recent().toISOString(),
      microservicesCount: faker.number.int({ min: 3, max: 8 }),
      proposalsCount: faker.number.int({ min: 0, max: 25 })
    }))

    const start = (page - 1) * limit
    const end = start + limit
    
    return HttpResponse.json({
      data: projects.slice(start, end),
      meta: {
        page,
        limit,
        total: projects.length,
        totalPages: Math.ceil(projects.length / limit)
      }
    })
  }),

  // Microservices handlers
  http.get('/api/v1/microservices/recommended', ({ request }) => {
    const opportunities = Array.from({ length: 30 }, (_, i) => ({
      id: faker.string.uuid(),
      title: faker.hacker.phrase(),
      description: faker.lorem.paragraph(3),
      estimatedHours: faker.number.int({ min: 20, max: 160 }),
      budget: faker.number.int({ min: 2000, max: 15000 }),
      complexity: faker.helpers.arrayElement(['EASY', 'MEDIUM', 'HARD']),
      requiredSkills: faker.helpers.arrayElements([
        'React', 'Node.js', 'Python', 'TypeScript', 'PostgreSQL', 
        'Docker', 'AWS', 'GraphQL', 'Redux'
      ], { min: 2, max: 5 }),
      deadline: faker.date.future().toISOString(),
      company: {
        name: faker.company.name(),
        logo: faker.image.avatar()
      },
      project: {
        title: faker.commerce.productName()
      },
      matchScore: faker.number.int({ min: 65, max: 98 }),
      applicationsCount: faker.number.int({ min: 0, max: 15 })
    }))

    return HttpResponse.json(opportunities)
  }),

  // WebSocket mock
  http.get('/socket.io/*', () => {
    return new HttpResponse(null, { status: 101 })
  })
]

// src/lib/api/mock/browser.ts
import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers)

// src/app/providers.tsx
'use client'

import { useEffect, useState } from 'react'

export function MockProvider({ children }: { children: React.ReactNode }) {
  const [isMockingEnabled, setIsMockingEnabled] = useState(false)

  useEffect(() => {
    if (process.env.NODE_ENV === 'development' && process.env.NEXT_PUBLIC_USE_MOCK === 'true') {
      import('../lib/api/mock/browser').then(({ worker }) => {
        worker.start({
          onUnhandledRequest: 'bypass'
        }).then(() => {
          setIsMockingEnabled(true)
        })
      })
    } else {
      setIsMockingEnabled(true)
    }
  }, [])

  if (!isMockingEnabled) {
    return <div>Carregando...</div>
  }

  return children
}
```

### API Client
```typescript
// src/lib/api/client.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth.store'

const baseURL = process.env.NEXT_PUBLIC_USE_MOCK === 'true' 
  ? 'http://localhost:3000'  // Next.js dev server para MSW
  : process.env.NEXT_PUBLIC_API_URL

export const apiClient = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor para adicionar token
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor para refresh token
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        await useAuthStore.getState().refreshToken()
        const newToken = useAuthStore.getState().token
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// API methods
export const api = {
  auth: {
    signIn: (data: { email: string; password: string }) =>
      apiClient.post('/api/v1/auth/sign-in/email', data),
    signUp: (data: { email: string; password: string; type: string }) =>
      apiClient.post('/api/v1/auth/sign-up/email', data),
    signOut: () => apiClient.post('/api/v1/auth/sign-out'),
    refresh: () => apiClient.post('/api/v1/auth/refresh')
  },

  projects: {
    list: (params?: any) => apiClient.get('/api/v1/projects', { params }),
    create: (data: any) => apiClient.post('/api/v1/projects', data),
    get: (id: string) => apiClient.get(`/api/v1/projects/${id}`),
    update: (id: string, data: any) => apiClient.put(`/api/v1/projects/${id}`, data),
    publish: (id: string) => apiClient.post(`/api/v1/projects/${id}/publish`)
  },

  microservices: {
    getRecommended: (params?: any) => 
      apiClient.get('/api/v1/microservices/recommended', { params })
  },

  proposals: {
    list: (params?: any) => apiClient.get('/api/v1/proposals', { params }),
    create: (data: any) => apiClient.post('/api/v1/microservices/${data.microserviceId}/proposals', data),
    get: (id: string) => apiClient.get(`/api/v1/proposals/${id}`)
  }
}
```

## ⚡ PERFORMANCE E OTIMIZAÇÕES

### Next.js 15.4.5 Configuration
```typescript
// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Turbopack para dev (nativo no Next.js 15)
  turbo: {
    rules: {
      '*.svg': {
        loaders: ['@svgr/webpack'],
        as: '*.js'
      }
    }
  },

  // Configurações de produção
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production'
  },

  // Otimizações de imagem
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.amazonaws.com'
      },
      {
        protocol: 'https',
        hostname: 'images.unsplash.com'
      }
    ]
  },

  // Experimental features
  experimental: {
    optimizePackageImports: [
      '@radix-ui/react-icons',
      'lucide-react'
    ]
  },

  // Webpack config
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, './src')
    }
    return config
  }
}

export default nextConfig
```

### Lazy Loading Components
```typescript
// src/components/LazyComponents.tsx
import dynamic from 'next/dynamic'

// Charts components
export const RevenueChart = dynamic(
  () => import('./charts/RevenueChart').then(mod => ({ default: mod.RevenueChart })),
  { 
    loading: () => <ChartSkeleton />,
    ssr: false 
  }
)

export const RichTextEditor = dynamic(
  () => import('./editor/RichTextEditor'),
  { 
    loading: () => <EditorSkeleton />,
    ssr: false 
  }
)

export const CommandPalette = dynamic(
  () => import('./CommandPalette'),
  { 
    loading: () => null,
    ssr: false 
  }
)
```

### Image Optimization
```typescript
// src/components/ui/OptimizedImage.tsx
import Image from 'next/image'
import { useState } from 'react'
import { cn } from '@/lib/utils'

interface OptimizedImageProps {
  src: string
  alt: string
  width?: number
  height?: number
  className?: string
  priority?: boolean
}

export const OptimizedImage = ({
  src,
  alt,
  width,
  height,
  className,
  priority = false
}: OptimizedImageProps) => {
  const [isLoading, setIsLoading] = useState(true)

  return (
    <div className={cn("relative overflow-hidden", className)}>
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        priority={priority}
        className={cn(
          "duration-700 ease-in-out",
          isLoading ? "scale-110 blur-2xl grayscale" : "scale-100 blur-0 grayscale-0"
        )}
        onLoad={() => setIsLoading(false)}
      />
    </div>
  )
}
```

## 🧪 TESTING

### Testing Setup
```typescript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/test/setup.ts'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testPathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/node_modules/'],
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': ['babel-jest', { presets: ['next/babel'] }]
  }
}

// src/test/setup.ts
import '@testing-library/jest-dom'
import { server } from './mocks/server'

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

### Component Tests
```typescript
// src/components/ui/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from './Button'

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('handles click events', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    fireEvent.click(screen.getByText('Click me'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('applies variant styles correctly', () => {
    render(<Button variant="destructive">Delete</Button>)
    const button = screen.getByText('Delete')
    expect(button).toHaveClass('bg-destructive')
  })

  it('disables button when loading', () => {
    render(<Button disabled>Loading</Button>)
    const button = screen.getByText('Loading')
    expect(button).toBeDisabled()
    expect(button).toHaveClass('opacity-50')
  })
})
```

### Integration Tests
```typescript
// src/features/auth/Login.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { LoginForm } from './LoginForm'
import { server } from '@/test/mocks/server'
import { rest } from 'msw'

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  })
  
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('LoginForm', () => {
  it('successfully logs in user', async () => {
    const onSuccess = jest.fn()
    
    render(
      <TestWrapper>
        <LoginForm onSuccess={onSuccess} />
      </TestWrapper>
    )

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' }
    })
    
    fireEvent.change(screen.getByLabelText(/senha/i), {
      target: { value: 'password123' }
    })

    fireEvent.click(screen.getByRole('button', { name: /entrar/i }))

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith({
        user: expect.objectContaining({ email: 'test@example.com' }),
        token: expect.any(String)
      })
    })
  })

  it('shows error message on failed login', async () => {
    server.use(
      rest.post('/api/v1/auth/sign-in/email', (req, res, ctx) => {
        return res(ctx.status(401), ctx.json({ message: 'Invalid credentials' }))
      })
    )

    render(
      <TestWrapper>
        <LoginForm onSuccess={() => {}} />
      </TestWrapper>
    )

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'invalid@example.com' }
    })
    
    fireEvent.change(screen.getByLabelText(/senha/i), {
      target: { value: 'wrongpassword' }
    })

    fireEvent.click(screen.getByRole('button', { name: /entrar/i }))

    await waitFor(() => {
      expect(screen.getByText(/credenciais inválidas/i)).toBeInTheDocument()
    })
  })
})
```

## 🚀 DEPLOYMENT

### Package.json Scripts
```json
{
  "name": "demandei-web",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev --turbo",
    "dev:mock": "NEXT_PUBLIC_USE_MOCK=true next dev --turbo",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "lint:fix": "next lint --fix",
    "type-check": "tsc --noEmit",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "analyze": "ANALYZE=true npm run build"
  }
}
```

### Environment Variables
```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:3333
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Auth
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000

# OAuth providers
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id
NEXT_PUBLIC_GITHUB_CLIENT_ID=your-github-client-id

# Analytics
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX
NEXT_PUBLIC_VERCEL_ANALYTICS=true

# Feature flags
NEXT_PUBLIC_ENABLE_PWA=true
NEXT_PUBLIC_ENABLE_CHAT=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
```

### Vercel Deployment
```json
// vercel.json
{
  "framework": "nextjs",
  "buildCommand": "pnpm build",
  "devCommand": "pnpm dev",
  "installCommand": "pnpm install",
  "outputDirectory": ".next",
  "regions": ["gru1"],
  "functions": {
    "src/app/api/**/*.ts": {
      "maxDuration": 30
    }
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "Referrer-Policy",
          "value": "origin-when-cross-origin"
        }
      ]
    }
  ]
}
```

## 📊 MÉTRICAS E MONITORAMENTO

### Web Vitals
```typescript
// src/lib/analytics/web-vitals.ts
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals'

type Metric = {
  name: string
  value: number
  id: string
  delta: number
}

const vitalsUrl = 'https://vitals.vercel-analytics.com/v1/vitals'

function getConnectionSpeed(): string {
  const connection = (navigator as any).connection
  if (connection) {
    return connection.effectiveType || 'unknown'
  }
  return 'unknown'
}

function sendToAnalytics(metric: Metric) {
  const body = {
    dsn: process.env.NEXT_PUBLIC_VERCEL_ANALYTICS_ID,
    id: metric.id,
    page: window.location.pathname,
    href: window.location.href,
    event_name: metric.name,
    value: metric.value.toString(),
    speed: getConnectionSpeed(),
  }

  if (navigator.sendBeacon) {
    navigator.sendBeacon(vitalsUrl, JSON.stringify(body))
  } else {
    fetch(vitalsUrl, {
      body: JSON.stringify(body),
      method: 'POST',
      keepalive: true,
    })
  }
}

export function reportWebVitals() {
  getCLS(sendToAnalytics)
  getFID(sendToAnalytics)
  getFCP(sendToAnalytics)
  getLCP(sendToAnalytics)
  getTTFB(sendToAnalytics)
}

// src/app/layout.tsx - adicionar no RootLayout
useEffect(() => {
  if (process.env.NODE_ENV === 'production') {
    reportWebVitals()
  }
}, [])
```

## 🎯 ROADMAP E PRÓXIMOS PASSOS

### Fase 1 - MVP (Atual)
- [x] Setup inicial Next.js 15.4.5
- [x] Design system com Tailwind v4
- [x] Layout Hybrid Command Center
- [x] Sistema de autenticação
- [x] Painéis básicos funcionais
- [ ] Sistema de mock completo
- [ ] Testes unitários > 80%
- [ ] Landing page otimizada

### Fase 2 - Integração (Meses 3-4)
- [ ] Integração com backend real
- [ ] WebSockets para chat e notificações
- [ ] Sistema de pagamentos UI
- [ ] PWA completa com offline
- [ ] Analytics e métricas

### Fase 3 - Escala (Meses 5-6)
- [ ] Otimizações de performance avançadas
- [ ] Internacionalização (i18n)
- [ ] A/B testing framework
- [ ] Features premium
- [ ] Mobile app (React Native)

## 📋 CHECKLIST DE ENTREGA MVP

### Funcionalidades Core
- [ ] Sistema de autenticação completo
- [ ] Dashboard responsivo para todos perfis
- [ ] CRUD de projetos com wizard
- [ ] Sistema de propostas
- [ ] Chat em tempo real
- [ ] Notificações push
- [ ] Sistema de mock funcional

### Performance e Qualidade
- [ ] Loading < 2s (LCP)
- [ ] Score Lighthouse > 90
- [ ] Testes unitários > 80% coverage
- [ ] Responsividade perfeita
- [ ] Acessibilidade WCAG 2.1 AA
- [ ] SEO otimizado

### Deploy e Monitoramento
- [ ] Deploy automatizado na Vercel
- [ ] Environment variables configuradas
- [ ] Error tracking (Sentry)
- [ ] Analytics configurado
- [ ] Web Vitals monitoring

## 💡 CONSIDERAÇÕES FINAIS

Este escopo completo do frontend oferece:

### ✅ **Vantagens Técnicas**
- **Stack Moderna**: Next.js 15.4.5 + React 19.1.1 + Tailwind v4
- **Performance Otimizada**: Turbopack, lazy loading, otimizações automáticas
- **DX Excelente**: TypeScript, ESLint, Prettier, hot reload
- **Escalabilidade**: Arquitetura modular, code splitting
- **Testing Completo**: Jest, RTL, MSW, coverage reports

### ✅ **Experiência do Usuário**
- **Design Moderno**: Hybrid Command Center sem sidebar tradicional
- **Responsividade Total**: Mobile-first design
- **Performance**: Loading rápido, animações suaves
- **Acessibilidade**: WCAG 2.1 AA compliance
- **PWA**: Funciona offline, push notifications

### ✅ **Desenvolvimento Ágil**
- **Mock System**: Desenvolvimento independente do backend
- **Hot Reload**: Feedback imediato durante desenvolvimento  
- **Component Library**: Reutilização de código
- **Type Safety**: TypeScript em todo o projeto
- **Error Handling**: Tratamento robusto de erros

Este frontend está preparado para escalar junto com o crescimento da plataforma Demandei, oferecendo uma base sólida para o MVP e evolução futura.