import { useEffect, useState, useMemo } from "react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useBrands } from "@/context/BrandContext";
import {
  Plus, Trash2, UserCog, Check, X, ShieldCheck, Sparkles, Search, Phone, PhoneCall, Building2, Shield, Layers, Pencil, Send, Mail, Key
} from "lucide-react";

const MODULE_PERMISSIONS = [
  { id: "crm", label: "CRM & Sales" },
  { id: "accounting", label: "Accounting & Finance" },
  { id: "inventory", label: "Warehouse & Inventory" },
  { id: "marketing", label: "Digital Marketing & Social" },
  { id: "projects", label: "Projects & Production" },
  { id: "work_orders", label: "Work Orders & AMCs" },
  { id: "team", label: "Team & Permissions" },
  { id: "settings", label: "System Settings" },
];

const DEPARTMENTS = [
  "All Departments",
  "Management",
  "Sales",
  "Marketing",
  "Service",
  "AMC & Tender",
  "Application Engineering",
  "Design Team",
  "Store & Warehouse",
  "Accounts & Finance",
  "Administration",
  "HR Department",
  "Pantry & Logistics"
];

export default function Team() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === "superadmin" || user?.role === "admin";

  const [activeTab, setActiveTab] = useState("users");
  const [deptFilter, setDeptFilter] = useState("All Departments");
  const [search, setSearch] = useState("");
  const [msg, setMsg] = useState("");

  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  // Brand permissions are granted against the shared brand list, so what an admin
  // can assign here is exactly what the rest of the app offers.
  const { brands } = useBrands();
  const [requests, setRequests] = useState([]);

  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingId] = useState(null);
  const [showRoleModal, setShowRoleModal] = useState(false);

  const [userForm, setUserForm] = useState({
    name: "", email: "", password: "", role: "sales", department: "Sales",
    extension: "", phone: "", designation: "", allowed_brands: []
  });
  const [roleForm, setRoleForm] = useState({ name: "", display_name: "", description: "", permissions: [] });
  const [err, setErr] = useState("");

  const load = () => {
    Promise.all([
      api.get("/users"),
      api.get("/roles").catch(() => ({ data: [] })),
      api.get("/brand-access-requests", { params: { status_filter: "pending" } }).catch(() => ({ data: [] }))
    ]).then(([u, r, req]) => {
      setUsers(u.data || []);
      setRoles(r.data || []);
      setRequests(req.data || []);
    });
  };

  useEffect(() => { load(); }, []);

  const openAddUser = () => {
    setEditingId(null);
    setUserForm({
      name: "", email: "", password: "Hitech@F12", role: "sales", department: "Sales",
      extension: "", phone: "", designation: "",
      allowed_brands: brands.map((b) => b.name)
    });
    setShowUserModal(true);
  };

  const openEditUser = (u) => {
    setEditingId(u.id);
    setUserForm({
      name: u.name || "",
      email: u.email || "",
      password: "",
      role: u.role || "sales",
      department: u.department || "Sales",
      extension: u.extension || "",
      phone: u.phone || "",
      designation: u.designation || "",
      allowed_brands: u.allowed_brands || []
    });
    setShowUserModal(true);
  };

  const submitUser = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      if (editingUser) {
        const payload = { ...userForm };
        if (!payload.password) delete payload.password;
        await api.patch(`/users/${editingUser}`, payload);
        setMsg(`Updated employee details for ${userForm.name}`);
      } else {
        await api.post("/users", userForm);
        setMsg(`Created employee ${userForm.name} with email ${userForm.email}`);
      }
      setShowUserModal(false);
      setEditingId(null);
      load();
    } catch (e2) { setErr(formatApiError(e2)); }
  };

  const sendWelcomeEmail = async (userId, employeeName, email) => {
    try {
      const res = await api.post(`/users/${userId}/send-welcome-email`);
      setMsg(res.data?.message || `Welcome email sent to ${employeeName} (${email})!`);
    } catch (e) {
      alert("Error sending onboarding email: " + e.message);
    }
  };

  const submitRole = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.post("/roles", roleForm);
      setRoleForm({ name: "", display_name: "", description: "", permissions: [] });
      setShowRoleModal(false);
      load();
    } catch (e2) { setErr(formatApiError(e2)); }
  };

  const removeUser = async (id) => {
    if (!window.confirm("Remove this team employee?")) return;
    try {
      await api.delete(`/users/${id}`);
      load();
    } catch (e) { alert(formatApiError(e)); }
  };

  const deleteCustomRole = async (roleId) => {
    if (!window.confirm("Delete this custom role?")) return;
    try {
      await api.delete(`/roles/${roleId}`);
      load();
    } catch (e) { alert(formatApiError(e)); }
  };

  const toggleBrandInUserForm = (brandName) => {
    setUserForm((prev) => {
      const current = new Set(prev.allowed_brands || []);
      if (current.has(brandName)) current.delete(brandName);
      else current.add(brandName);
      return { ...prev, allowed_brands: Array.from(current) };
    });
  };

  const actionRequest = async (id, action) => {
    await api.patch(`/brand-access-requests/${id}`, { action });
    load();
  };

  const togglePermission = (permId) => {
    setRoleForm((prev) => {
      const current = new Set(prev.permissions || []);
      if (current.has(permId)) current.delete(permId);
      else current.add(permId);
      return { ...prev, permissions: Array.from(current) };
    });
  };

  const filteredUsers = useMemo(() => {
    let list = users;
    if (deptFilter !== "All Departments") {
      list = list.filter((u) => (u.department || "").toLowerCase() === deptFilter.toLowerCase());
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((u) =>
        `${u.name} ${u.email} ${u.extension || ""} ${u.department || ""} ${u.designation || ""} ${u.phone || ""}`.toLowerCase().includes(q)
      );
    }
    return list;
  }, [users, deptFilter, search]);

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto space-y-6 bg-white text-slate-900 min-h-screen" data-testid="team-page">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="label-eyebrow mb-2">Corporate Staff Directory & ACL</div>
          <h1 className="font-display text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <ShieldCheck className="w-8 h-8 text-sky-600" /> Employee Directory & Roles
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            {users.length} staff members across departments · Extension directory, emails, brand ACLs & onboarding
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowRoleModal(true)}
            className="inline-flex items-center gap-2 bg-slate-100 border border-slate-300 text-slate-800 px-4 py-2.5 rounded-xl text-xs font-bold hover:bg-slate-200 transition-all cursor-pointer"
          >
            <Shield className="w-4 h-4 text-sky-600" /> Create Custom Role
          </button>
          <button
            onClick={openAddUser}
            data-testid="team-add-btn"
            className="inline-flex items-center gap-2 bg-sky-600 text-white px-5 py-2.5 rounded-xl text-xs font-bold hover:bg-sky-500 shadow-md shadow-sky-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" /> Add Staff Member
          </button>
        </div>
      </header>

      {msg && (
        <div className="p-4 rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-800 text-xs flex items-center justify-between font-bold">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>{msg}</span>
          </div>
          <button onClick={() => setMsg("")} className="hover:text-slate-900 text-slate-500">Dismiss</button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex gap-2 border-b border-slate-200 pb-1">
        <button
          onClick={() => setActiveTab("users")}
          className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === "users" ? "bg-slate-900 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Employee Directory ({users.length})
        </button>
        <button
          onClick={() => setActiveTab("roles")}
          className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === "roles" ? "bg-slate-900 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Role Management Matrix ({roles.length})
        </button>
      </div>

      {/* Department Filter Pills */}
      {activeTab === "users" && (
        <div className="space-y-3">
          <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
            {DEPARTMENTS.map((dept) => (
              <button
                key={dept}
                onClick={() => setDeptFilter(dept)}
                className={`whitespace-nowrap px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                  deptFilter === dept
                    ? "bg-sky-600 text-white border-sky-600 shadow-xs"
                    : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                }`}
              >
                {dept}
              </button>
            ))}
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-center justify-between gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search staff by name, email, extension, dept, phone..."
                className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500"
              />
            </div>
            <span className="text-xs text-slate-500 font-bold">Showing {filteredUsers.length} staff members</span>
          </div>
        </div>
      )}

      {/* Pending Brand Access Requests */}
      {requests.length > 0 && (
        <div className="p-5 rounded-2xl bg-amber-50 border border-amber-200 space-y-3" data-testid="pending-requests">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
            <ShieldCheck className="w-4 h-4 text-amber-600" />
            <span>Pending Brand Access Requests ({requests.length})</span>
          </div>
          <div className="space-y-2">
            {requests.map((r) => (
              <div key={r.id} className="bg-white border border-amber-200 rounded-xl p-3 flex items-center justify-between gap-4 shadow-2xs">
                <div className="text-xs">
                  <span className="font-bold text-slate-900">{r.user_name}</span>
                  <span className="text-slate-500"> requests catalog access to </span>
                  <span className="font-bold text-sky-700">{r.brand}</span>
                  {r.reason && <span className="text-slate-500 italic ml-2">"{r.reason}"</span>}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => actionRequest(r.id, "approve")} className="px-3 py-1 rounded-lg text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500">
                    Approve
                  </button>
                  <button onClick={() => actionRequest(r.id, "deny")} className="px-3 py-1 rounded-lg text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200">
                    Deny
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 1: Staff Directory View */}
      {activeTab === "users" && (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-100/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200 font-bold">
                <tr>
                  <th className="px-6 py-4 font-bold">Staff Member & Email</th>
                  <th className="px-6 py-4 font-bold">Ext #</th>
                  <th className="px-6 py-4 font-bold">Department & Designation</th>
                  <th className="px-6 py-4 font-bold">Contact Phone</th>
                  <th className="px-6 py-4 font-bold">Assigned Role</th>
                  <th className="px-6 py-4 font-bold">Brand Catalog Access</th>
                  <th className="px-6 py-4 font-bold text-right">Actions & Onboarding</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50 transition-colors group" data-testid={`user-row-${u.id}`}>
                    <td className="px-6 py-4 font-bold text-slate-900">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center font-display font-black text-xs shrink-0">
                          {u.name[0]?.toUpperCase()}
                        </div>
                        <div>
                          <div className="font-bold text-slate-900">{u.name}</div>
                          <div className="text-xs text-sky-700 font-mono font-semibold">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {u.extension ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono font-extrabold bg-sky-50 text-sky-800 border border-sky-200">
                          <PhoneCall className="w-3 h-3 text-sky-600" /> Ext {u.extension}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs font-medium">
                      <div className="font-bold text-slate-900">{u.department || "Operations"}</div>
                      <div className="text-slate-500">{u.designation || "Staff"}</div>
                    </td>
                    <td className="px-6 py-4 text-xs font-mono font-medium text-slate-700">
                      {u.phone ? `+91 ${u.phone}` : "—"}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold uppercase bg-slate-100 text-slate-800 border border-slate-200">
                        {u.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {["admin", "superadmin"].includes(u.role) ? (
                        <span className="text-xs text-emerald-700 font-bold bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">All Brands Granted</span>
                      ) : (
                        <div className="flex flex-wrap gap-1 max-w-xs max-h-16 overflow-y-auto no-scrollbar">
                          {(u.allowed_brands || []).map((b) => (
                            <span key={b} className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200">
                              {b}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="inline-flex items-center gap-1.5 justify-end">
                        {/* Send Welcome Email */}
                        <button
                          onClick={() => sendWelcomeEmail(u.id, u.name, u.email)}
                          className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 px-2.5 py-1 rounded-lg transition-all cursor-pointer"
                          title="Send Welcome & Onboarding Email with Credentials"
                        >
                          <Send className="w-3 h-3 text-indigo-600" /> Send Mail
                        </button>

                        {/* Edit Employee Details */}
                        <button
                          onClick={() => openEditUser(u)}
                          className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-700 bg-slate-100 border border-slate-300 hover:bg-slate-200 px-2 py-1 rounded-lg transition-all cursor-pointer"
                          title="Edit Employee Details & Brand Access"
                        >
                          <Pencil className="w-3 h-3 text-slate-700" /> Edit
                        </button>

                        {!["admin", "superadmin"].includes(u.role) && (
                          <button onClick={() => removeUser(u.id)} className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Roles Matrix View */}
      {activeTab === "roles" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {roles.map((r) => (
            <div key={r.id || r.name} className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold uppercase tracking-widest text-sky-700">{r.name}</span>
                  {r.is_system ? (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">System Built-In</span>
                  ) : (
                    <button onClick={() => deleteCustomRole(r.id)} className="text-slate-400 hover:text-rose-600 p-1">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <h3 className="font-display text-lg font-bold text-slate-900">{r.display_name}</h3>
                <p className="text-xs text-slate-600 font-medium leading-relaxed">{r.description || "System role definition."}</p>
              </div>

              <div className="pt-3 border-t border-slate-100">
                <div className="text-[10px] uppercase font-bold text-slate-400 mb-2">Module Access Permissions:</div>
                <div className="flex flex-wrap gap-1.5">
                  {(r.permissions || []).map((perm, i) => (
                    <span key={i} className="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-sky-50 text-sky-800 border border-sky-200 capitalize">
                      {perm}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Employee Modal */}
      {showUserModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-2xl p-6 space-y-4 shadow-2xl animate-scale-in max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-display text-xl font-bold text-slate-900">
                {editingUser ? "Edit Employee Details & Brand Access" : "Add New Staff Member"}
              </h3>
              <button onClick={() => setShowUserModal(false)} className="text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
            </div>

            {err && <div className="p-3 text-xs bg-rose-50 border border-rose-200 text-rose-700 rounded-xl font-bold">{err}</div>}

            <form onSubmit={submitUser} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Full Name *</label>
                  <input required type="text" value={userForm.name} onChange={(e) => setUserForm({ ...userForm, name: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Email Address (@hitechavl.com) *</label>
                  <input required type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500 font-mono" />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Mobile Phone</label>
                  <input type="text" value={userForm.phone} onChange={(e) => setUserForm({ ...userForm, phone: e.target.value })} placeholder="e.g. 9871059125" className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Extension No.</label>
                  <input type="text" value={userForm.extension} onChange={(e) => setUserForm({ ...userForm, extension: e.target.value })} placeholder="e.g. 301" className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500 font-mono" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Designation</label>
                  <input type="text" value={userForm.designation} onChange={(e) => setUserForm({ ...userForm, designation: e.target.value })} placeholder="e.g. Senior Sales Manager" className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500" />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Department</label>
                  <select value={userForm.department} onChange={(e) => setUserForm({ ...userForm, department: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-sky-500">
                    {DEPARTMENTS.filter((d) => d !== "All Departments").map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Assigned System Role</label>
                  <select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })} className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-sky-500">
                    {roles.map((r) => <option key={r.name} value={r.name}>{r.display_name || r.name}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">
                  Password {editingUser && "(Leave blank to keep unchanged, default: Hitech@F12)"}
                </label>
                <input
                  type="password"
                  value={userForm.password}
                  onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                  placeholder={editingUser ? "••••••••" : "Hitech@F12"}
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-sm text-slate-900 font-medium focus:outline-none focus:border-sky-500"
                />
              </div>

              {/* All 19 Brands Access Matrix */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-sky-700">Manufacturer Brands Granted ({userForm.allowed_brands?.length || 0} / {brands.length})</label>
                  <button
                    type="button"
                    onClick={() => setUserForm({ ...userForm, allowed_brands: brands.map((b) => b.name) })}
                    className="text-[10px] font-bold text-sky-700 hover:underline"
                  >
                    Select All Brands
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 bg-slate-50 p-3 rounded-xl border border-slate-200 max-h-48 overflow-y-auto">
                  {brands.map((b) => {
                    const checked = (userForm.allowed_brands || []).includes(b.name);
                    return (
                      <label key={b.id || b.name} className="flex items-center gap-2 text-xs font-bold text-slate-800 cursor-pointer select-none p-1 rounded hover:bg-white">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleBrandInUserForm(b.name)}
                          className="rounded text-sky-600 focus:ring-sky-500"
                        />
                        <span className="truncate">{b.name}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowUserModal(false)} className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-900">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500">
                  {editingUser ? "Update Employee" : "Create Employee"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Custom Role Modal */}
      {showRoleModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-xl p-6 space-y-4 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-display text-xl font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-sky-600" /> Create Custom User Role
              </h3>
              <button onClick={() => setShowRoleModal(false)} className="text-slate-400 hover:text-slate-800"><X className="w-5 h-5" /></button>
            </div>
            {err && <div className="p-3 text-xs bg-rose-50 border border-rose-200 text-rose-700 rounded-xl">{err}</div>}

            <form onSubmit={submitRole} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Role Key (ID) *</label>
                  <input required type="text" value={roleForm.name} onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })} placeholder="e.g. engineering" className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-sky-500 font-mono" />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Display Title *</label>
                  <input required type="text" value={roleForm.display_name} onChange={(e) => setRoleForm({ ...roleForm, display_name: e.target.value })} placeholder="e.g. Systems Engineer" className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-sky-500" />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-1">Role Description</label>
                <textarea rows={2} value={roleForm.description} onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })} placeholder="Describe access responsibilities..." className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-sky-500" />
              </div>

              <div>
                <label className="text-xs font-bold uppercase text-slate-700 block mb-2">Module Access Permissions</label>
                <div className="grid grid-cols-2 gap-2 bg-slate-50 p-3 rounded-xl border border-slate-200">
                  {MODULE_PERMISSIONS.map((mp) => {
                    const checked = (roleForm.permissions || []).includes(mp.id);
                    return (
                      <label key={mp.id} className="flex items-center gap-2 text-xs font-bold text-slate-800 cursor-pointer select-none p-1.5 hover:bg-white rounded-lg">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => togglePermission(mp.id)}
                          className="rounded text-sky-600 focus:ring-sky-500"
                        />
                        <span>{mp.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                <button type="button" onClick={() => setShowRoleModal(false)} className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-900">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500">Save Custom Role</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
