import { Plus, LayoutGrid, Target, PieChart, BarChart3, FileText, Crown, Tag, Calendar, List, FolderKanban, CheckSquare, ShoppingCart, Truck, Bell } from "lucide-react";

import LeadsWidget from "@/components/dashboard/widgets/LeadsWidget";
import LeadsInflowWidget from "@/components/dashboard/widgets/LeadsInflowWidget";
import { LeadSourcesWidget, QuotationStatusWidget } from "@/components/dashboard/widgets/DonutWidgets";
import PipelineByStageWidget from "@/components/dashboard/widgets/PipelineByStageWidget";
import {
  TopRepsWidget,
  BrandInterestWidget,
  FollowUpsWidget,
  OperationsWidget,
  RecentLeadsWidget,
} from "@/components/dashboard/widgets/Panels";
import {
  ProjectsWidget,
  TasksWidget,
  PurchaseOrdersWidget,
  NotificationsWidget,
  SalesSummaryWidget,
} from "@/components/dashboard/widgets/DeliveryWidgets";

/**
 * The widget registry: adding a dashboard widget is one entry here plus the
 * matching id in the backend WIDGET_REGISTRY. Nothing else in the dashboard needs
 * to change, which is the whole point -- the old dashboard was a single linear
 * JSX tree where every new widget meant editing the page.
 *
 * `bare: true` means the component renders its own outer card (because it spans
 * a row of sub-cards or provides its own header), so no WidgetShell chrome wraps it.
 */
export const WIDGETS = {
  kpi_leads: { label: "Lead KPIs", icon: LayoutGrid, component: LeadsWidget, bare: true, full: true },
  leads_inflow: { label: "Lead Inflow", icon: Target, component: LeadsInflowWidget },
  lead_sources: { label: "Lead Sources", icon: PieChart, component: LeadSourcesWidget },
  pipeline_by_stage: { label: "Pipeline by Stage", icon: BarChart3, component: PipelineByStageWidget },
  quotation_status: { label: "Quotation Status", icon: PieChart, component: QuotationStatusWidget },
  sales_summary: { label: "Sales Summary", icon: FileText, component: SalesSummaryWidget },
  top_reps: { label: "Top Sales Reps", icon: Crown, component: TopRepsWidget },
  brand_interest: { label: "Manufacturer Mentions", icon: Tag, component: BrandInterestWidget },
  follow_ups: { label: "Follow-up Schedule", icon: Calendar, component: FollowUpsWidget },
  recent_leads: { label: "Latest Lead Enquiries", icon: List, component: RecentLeadsWidget, bare: true },
  projects: { label: "Projects", icon: FolderKanban, component: ProjectsWidget, bare: true },
  tasks: { label: "Tasks", icon: CheckSquare, component: TasksWidget, bare: true },
  purchase_orders: { label: "Purchase Orders", icon: ShoppingCart, component: PurchaseOrdersWidget, bare: true },
  operations: { label: "Operations", icon: Truck, component: OperationsWidget, bare: true },
  notifications: { label: "Notifications", icon: Bell, component: NotificationsWidget, bare: true },
};

/** Widget ids that come from /dashboard/summary rather than /dashboard/stats. */
const SUMMARY_KEYS = {
  projects: "projects",
  tasks: "tasks",
  purchase_orders: "purchase_orders",
  notifications: "notifications",
};

export function WidgetBody({ id, stats, summary }) {
  const entry = WIDGETS[id];
  if (!entry) return null;
  const Component = entry.component;
  const key = SUMMARY_KEYS[id];
  return <Component stats={stats} data={key ? summary?.[key] : undefined} />;
}

/** Columns per breakpoint. The 12-col grid lets a widget span any width. */
export function spanClass(w) {
  const n = Math.max(1, Math.min(12, Number(w) || 3));
  if (n >= 12) return "col-span-12";
  if (n >= 8) return "col-span-12 lg:col-span-8";
  if (n >= 6) return "col-span-12 md:col-span-6 lg:col-span-6";
  if (n >= 4) return "col-span-12 sm:col-span-6 lg:col-span-4";
  return "col-span-12 sm:col-span-6 lg:col-span-3";
}

export const AddWidgetIcon = Plus;
