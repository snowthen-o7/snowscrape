// Local layout components
export { MarketingLayout } from './MarketingLayout';

// SnowScrape-specific AppLayout wrapper (pre-configured with nav items)
export { AppLayout, SnowScrapeLayout } from './SnowScrapeLayout';

// Re-export base layout components and types from @snowforge/ui for customization
export {
  AppLayout as BaseAppLayout,
  AppSidebar,
  AppTopNav,
  type AppLayoutProps,
  type AppSidebarProps,
  type AppTopNavProps,
  type NavItem,
  type QuickAction,
} from '@snowforge/ui';
