import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import AppShell from "@/components/layout/AppShell";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Leads from "@/pages/Leads";
import LeadDetail from "@/pages/LeadDetail";
import LeadForm from "@/pages/LeadForm";
import Pipeline from "@/pages/Pipeline";
import Quotations from "@/pages/Quotations";
import Team from "@/pages/Team";
import Catalog from "@/pages/Catalog";
import Packages from "@/pages/Packages";
import Shipments from "@/pages/Shipments";
import Inventory from "@/pages/Inventory";
import AMCs from "@/pages/AMCs";
import QuotationBuilder from "@/pages/QuotationBuilder";
import Integrations from "@/pages/Integrations";
import Import from "@/pages/Import";
import Webhooks from "@/pages/Webhooks";
import ResendSettings from "@/pages/ResendSettings";
import PublicLeadForm from "@/pages/PublicLeadForm";
import PublicQuotation from "@/pages/PublicQuotation";
import ProjectDetail from "@/pages/ProjectDetail";
import { Toaster } from "sonner";

// New ERP modules
import Projects from "@/pages/Projects";
import Customers from "@/pages/Customers";
import Contacts from "@/pages/Contacts";
import Accounting from "@/pages/Accounting";
import Calendar from "@/pages/Calendar";
import Tasks from "@/pages/Tasks";
import WorkOrders from "@/pages/WorkOrders";
import Suppliers from "@/pages/Suppliers";
import SocialMedia from "@/pages/SocialMedia";
import Marketing from "@/pages/DigitalMarketing";
import BookingSystem from "@/pages/BookingSystem";
import CustomerPortal from "@/pages/CustomerPortal";
import CompanySettings from "@/pages/CompanySettings";
import SystemSettings from "@/pages/SystemSettings";
import GenericModulePage from "@/pages/GenericModulePage";

// HiTech AVL Process Flow Modules
import Qualification from "@/pages/Qualification";
import FollowUps from "@/pages/FollowUps";
import DesignTeam from "@/pages/DesignTeam";
import BoqGenerator from "@/pages/BoqGenerator";
import PurchaseOrders from "@/pages/PurchaseOrders";

const ADMIN_ROLES = ["admin", "superadmin", "management"];

function Protected({ children, adminOnly = false }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-sm text-slate-500">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  // Mirrors the backend's is_admin_role(). Previously only role === "admin"
  // passed, so superadmin and management were locked out of admin-only routes
  // even though the sidebar and the API both grant them full access.
  if (adminOnly && !ADMIN_ROLES.includes((user.role || "").toLowerCase())) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster position="top-right" />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/capture" element={<PublicLeadForm />} />
          {/* Customer-facing share link: intentionally outside <Protected>. */}
          <Route path="/public/quotation/:token" element={<PublicQuotation />} />
          <Route
            element={
              <Protected>
                <AppShell />
              </Protected>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/leads" element={<Leads />} />
            <Route path="/leads/new" element={<LeadForm />} />
            <Route path="/leads/:id" element={<LeadDetail />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="/quotations" element={<Quotations />} />
            <Route path="/quotations/new" element={<QuotationBuilder />} />
            <Route path="/catalog" element={<Catalog />} />
            <Route path="/packages" element={<Packages />} />
            <Route path="/shipments" element={<Shipments />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/amcs" element={<AMCs />} />

            {/* New ERP Modules */}
            <Route path="/projects" element={<Projects />} />
      <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/accounting" element={<Accounting />} />
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/work-orders" element={<WorkOrders />} />
            <Route path="/suppliers" element={<Suppliers />} />
            <Route path="/social" element={<SocialMedia />} />
            <Route path="/marketing" element={<Marketing />} />
            <Route path="/booking" element={<BookingSystem />} />
            <Route path="/portal" element={<CustomerPortal />} />
            <Route path="/settings/company" element={<CompanySettings />} />
            <Route path="/settings/system" element={<SystemSettings />} />
            <Route path="/module/:moduleName" element={<GenericModulePage />} />

            {/* HiTech AVL Process Flow Modules */}
            <Route path="/qualification" element={<Qualification />} />
            <Route path="/follow-ups" element={<FollowUps />} />
            <Route path="/design-team" element={<DesignTeam />} />
            <Route path="/boq-generator" element={<BoqGenerator />} />
            <Route path="/purchase-orders" element={<PurchaseOrders />} />

            {/* Admin */}
            <Route path="/team" element={<Protected adminOnly><Team /></Protected>} />
            <Route path="/integrations" element={<Protected adminOnly><Integrations /></Protected>} />
            <Route path="/import" element={<Protected adminOnly><Import /></Protected>} />
            <Route path="/webhooks" element={<Protected adminOnly><Webhooks /></Protected>} />
            <Route path="/resend" element={<Protected adminOnly><ResendSettings /></Protected>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
