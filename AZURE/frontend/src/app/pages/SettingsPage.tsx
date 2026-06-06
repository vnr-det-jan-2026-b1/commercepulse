import { useState, useCallback } from "react";
import { toast, Toaster } from "sonner";
import {
  User,
  Bell,
  Lock,
  CreditCard,
  Users,
  Globe,
  Palette,
  Shield,
  Smartphone,
  Mail,
  Key,
  CheckCircle,
  Eye,
  EyeOff,
  Copy,
  Check,
  X,
  Plus,
  Trash2,
  Download,
  Upload,
  Monitor,
  Moon,
  Sun,
  Zap,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  Clock,
  MapPin,
  type LucideIcon,
} from "lucide-react";

/* ─── Tab registry ─── */
const tabs: { id: string; label: string; icon: LucideIcon }[] = [
  { id: "profile", label: "Profile", icon: User },
  { id: "account", label: "Account", icon: Lock },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "team", label: "Team", icon: Users },
  { id: "integrations", label: "Integrations", icon: Globe },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "security", label: "Security", icon: Shield },
];

/* ─────────────────────── Shared Helpers ─────────────────────── */

function SettingsCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-2xl p-8 shadow-sm border border-gray-100 ${className}`}>
      {children}
    </div>
  );
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h2 className="text-2xl font-semibold text-gray-900">{title}</h2>
      {subtitle && <p className="text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-gray-700 mb-2">{children}</label>;
}

const inputClass =
  "w-full px-4 py-3 border border-gray-200 rounded-xl bg-gray-50/60 focus:bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all text-gray-900 placeholder:text-gray-400";

function SaveCancelBar({ onSave, onCancel, saving = false }: { onSave: () => void; onCancel: () => void; saving?: boolean }) {
  return (
    <div className="flex justify-end gap-3 pt-6 border-t border-gray-100 mt-6">
      <button
        onClick={onCancel}
        className="px-6 py-2.5 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 font-medium transition-all"
      >
        Cancel
      </button>
      <button
        onClick={onSave}
        disabled={saving}
        className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all shadow-md shadow-purple-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      >
        {saving && <RefreshCw className="w-4 h-4 animate-spin" />}
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </div>
  );
}

function Toggle({
  enabled,
  onChange,
  size = "md",
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
  size?: "sm" | "md";
}) {
  const dims = size === "sm" ? "w-10 h-5" : "w-12 h-6";
  const thumb = size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4";
  const translate = size === "sm" ? "translate-x-5" : "translate-x-6";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className={`relative ${dims} rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2 ${
        enabled ? "bg-purple-600" : "bg-gray-300"
      }`}
    >
      <span
        className={`absolute top-0.5 left-0.5 ${thumb} bg-white rounded-full shadow transition-transform duration-200 ${
          enabled ? translate : ""
        }`}
      />
    </button>
  );
}

function ConfirmModal({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = "Confirm",
  danger = false,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmLabel?: string;
  danger?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-start gap-4 mb-6">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${danger ? "bg-red-100" : "bg-purple-100"}`}>
            <AlertTriangle className={`w-6 h-6 ${danger ? "text-red-600" : "text-purple-600"}`} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <p className="text-gray-500 mt-1 text-sm">{description}</p>
          </div>
        </div>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-5 py-2.5 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 font-medium transition-all">
            Cancel
          </button>
          <button
            onClick={() => { onConfirm(); onClose(); }}
            className={`px-5 py-2.5 text-white rounded-xl font-medium transition-all ${
              danger ? "bg-red-600 hover:bg-red-700" : "bg-purple-600 hover:bg-purple-700"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────── Root Component ─────────────────────── */

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");

  return (
    <>
      <Toaster position="top-right" richColors closeButton />

      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-2">Manage your account settings and preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <nav className="bg-white rounded-2xl p-3 shadow-sm border border-gray-100 space-y-0.5 sticky top-6">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                    active
                      ? "bg-gradient-to-r from-purple-50 to-indigo-50 text-purple-700 shadow-sm"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`}
                >
                  <Icon className={`w-5 h-5 ${active ? "text-purple-600" : ""}`} />
                  <span className="font-medium text-sm">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3 space-y-6">
          {activeTab === "profile" && <ProfileTab />}
          {activeTab === "account" && <AccountTab />}
          {activeTab === "notifications" && <NotificationsTab />}
          {activeTab === "billing" && <BillingTab />}
          {activeTab === "team" && <TeamTab />}
          {activeTab === "integrations" && <IntegrationsTab />}
          {activeTab === "appearance" && <AppearanceTab />}
          {activeTab === "security" && <SecurityTab />}
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════
   1. PROFILE TAB
   ═══════════════════════════════════════════════════════════════ */

const defaultProfile = {
  firstName: "John",
  lastName: "Doe",
  email: "john.doe@commercepulse.com",
  phone: "+1 (555) 123-4567",
  bio: "E-commerce analytics specialist with 5+ years of experience in data-driven decision making.",
  company: "Brew Boulevard",
  role: "Store Owner",
  website: "https://brewboulevard.com",
};

function ProfileTab() {
  const [profile, setProfile] = useState({ ...defaultProfile });
  const [saving, setSaving] = useState(false);
  const [avatarHover, setAvatarHover] = useState(false);

  const update = (field: string, value: string) => setProfile((p) => ({ ...p, [field]: value }));

  const handleSave = useCallback(() => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("Profile updated successfully", { description: "Your changes have been saved." });
    }, 800);
  }, []);

  const handleCancel = () => setProfile({ ...defaultProfile });

  return (
    <SettingsCard>
      <SectionTitle title="Profile Information" subtitle="Update your personal details and public profile" />

      <div className="space-y-6">
        {/* Avatar */}
        <div>
          <FieldLabel>Profile Photo</FieldLabel>
          <div className="flex items-center gap-5">
            <div
              className="relative w-20 h-20 rounded-full cursor-pointer group"
              onMouseEnter={() => setAvatarHover(true)}
              onMouseLeave={() => setAvatarHover(false)}
            >
              <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-2xl font-semibold shadow-lg shadow-purple-200">
                {profile.firstName[0]}{profile.lastName[0]}
              </div>
              {avatarHover && (
                <div className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center transition-opacity">
                  <Upload className="w-5 h-5 text-white" />
                </div>
              )}
            </div>
            <div>
              <button
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
                onClick={() => toast.info("Photo upload", { description: "File picker would open here." })}
              >
                Upload Photo
              </button>
              <p className="text-xs text-gray-400 mt-1.5">JPG, PNG or GIF. Max size 2MB.</p>
            </div>
          </div>
        </div>

        {/* Name */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <FieldLabel>First Name</FieldLabel>
            <input type="text" value={profile.firstName} onChange={(e) => update("firstName", e.target.value)} className={inputClass} />
          </div>
          <div>
            <FieldLabel>Last Name</FieldLabel>
            <input type="text" value={profile.lastName} onChange={(e) => update("lastName", e.target.value)} className={inputClass} />
          </div>
        </div>

        {/* Email */}
        <div>
          <FieldLabel>Email Address</FieldLabel>
          <input type="email" value={profile.email} onChange={(e) => update("email", e.target.value)} className={inputClass} />
        </div>

        {/* Phone */}
        <div>
          <FieldLabel>Phone Number</FieldLabel>
          <input type="tel" value={profile.phone} onChange={(e) => update("phone", e.target.value)} className={inputClass} />
        </div>

        {/* Company & Role */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <FieldLabel>Company</FieldLabel>
            <input type="text" value={profile.company} onChange={(e) => update("company", e.target.value)} className={inputClass} />
          </div>
          <div>
            <FieldLabel>Role</FieldLabel>
            <input type="text" value={profile.role} onChange={(e) => update("role", e.target.value)} className={inputClass} />
          </div>
        </div>

        {/* Website */}
        <div>
          <FieldLabel>Website</FieldLabel>
          <input type="url" value={profile.website} onChange={(e) => update("website", e.target.value)} className={inputClass} />
        </div>

        {/* Bio */}
        <div>
          <FieldLabel>Bio</FieldLabel>
          <textarea
            rows={4}
            value={profile.bio}
            onChange={(e) => update("bio", e.target.value)}
            className={inputClass + " resize-none"}
            maxLength={250}
          />
          <p className="text-xs text-gray-400 mt-1 text-right">{profile.bio.length}/250</p>
        </div>

        <SaveCancelBar onSave={handleSave} onCancel={handleCancel} saving={saving} />
      </div>
    </SettingsCard>
  );
}

/* ═══════════════════════════════════════════════════════════════
   2. ACCOUNT TAB
   ═══════════════════════════════════════════════════════════════ */

function getPasswordStrength(pwd: string): { label: string; color: string; pct: number } {
  if (!pwd) return { label: "", color: "bg-gray-200", pct: 0 };
  let score = 0;
  if (pwd.length >= 8) score++;
  if (pwd.length >= 12) score++;
  if (/[A-Z]/.test(pwd)) score++;
  if (/[0-9]/.test(pwd)) score++;
  if (/[^A-Za-z0-9]/.test(pwd)) score++;
  if (score <= 1) return { label: "Weak", color: "bg-red-500", pct: 20 };
  if (score <= 2) return { label: "Fair", color: "bg-orange-500", pct: 40 };
  if (score <= 3) return { label: "Good", color: "bg-yellow-500", pct: 60 };
  if (score <= 4) return { label: "Strong", color: "bg-green-500", pct: 80 };
  return { label: "Very Strong", color: "bg-emerald-500", pct: 100 };
}

function AccountTab() {
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [deleteModal, setDeleteModal] = useState(false);
  const [language, setLanguage] = useState("en");
  const [timezone, setTimezone] = useState("America/Los_Angeles");

  const strength = getPasswordStrength(newPwd);
  const passwordsMatch = newPwd && confirmPwd && newPwd === confirmPwd;
  const passwordsMismatch = newPwd && confirmPwd && newPwd !== confirmPwd;

  const handlePasswordUpdate = () => {
    if (!currentPwd) { toast.error("Please enter your current password"); return; }
    if (!newPwd || newPwd.length < 8) { toast.error("New password must be at least 8 characters"); return; }
    if (newPwd !== confirmPwd) { toast.error("Passwords do not match"); return; }
    toast.success("Password updated", { description: "Your password has been changed successfully." });
    setCurrentPwd(""); setNewPwd(""); setConfirmPwd("");
  };

  const PasswordField = ({
    label, value, onChange, show, onToggle,
  }: { label: string; value: string; onChange: (v: string) => void; show: boolean; onToggle: () => void }) => (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={inputClass + " pr-12"}
          placeholder="••••••••"
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
        >
          {show ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Change Password */}
      <SettingsCard>
        <SectionTitle title="Change Password" subtitle="Ensure your account uses a strong, unique password" />
        <div className="space-y-4">
          <PasswordField label="Current Password" value={currentPwd} onChange={setCurrentPwd} show={showCurrent} onToggle={() => setShowCurrent(!showCurrent)} />
          <PasswordField label="New Password" value={newPwd} onChange={setNewPwd} show={showNew} onToggle={() => setShowNew(!showNew)} />

          {/* Strength Meter */}
          {newPwd && (
            <div className="space-y-1.5">
              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div className={`h-full ${strength.color} rounded-full transition-all duration-300`} style={{ width: `${strength.pct}%` }} />
              </div>
              <p className="text-xs text-gray-500">
                Password strength: <span className="font-medium">{strength.label}</span>
              </p>
            </div>
          )}

          <PasswordField label="Confirm New Password" value={confirmPwd} onChange={setConfirmPwd} show={showConfirm} onToggle={() => setShowConfirm(!showConfirm)} />

          {/* Match indicator */}
          {passwordsMatch && (
            <div className="flex items-center gap-1.5 text-green-600 text-sm">
              <CheckCircle className="w-4 h-4" /> Passwords match
            </div>
          )}
          {passwordsMismatch && (
            <div className="flex items-center gap-1.5 text-red-500 text-sm">
              <X className="w-4 h-4" /> Passwords do not match
            </div>
          )}

          <button
            onClick={handlePasswordUpdate}
            className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all shadow-md shadow-purple-200"
          >
            Update Password
          </button>
        </div>
      </SettingsCard>

      {/* Language & Timezone */}
      <SettingsCard>
        <SectionTitle title="Preferences" subtitle="Language and regional settings" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <FieldLabel>Language</FieldLabel>
            <select value={language} onChange={(e) => { setLanguage(e.target.value); toast.success("Language updated"); }} className={inputClass}>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="ja">Japanese</option>
            </select>
          </div>
          <div>
            <FieldLabel>Timezone</FieldLabel>
            <select value={timezone} onChange={(e) => { setTimezone(e.target.value); toast.success("Timezone updated"); }} className={inputClass}>
              <option value="America/Los_Angeles">Pacific Time (US)</option>
              <option value="America/Chicago">Central Time (US)</option>
              <option value="America/New_York">Eastern Time (US)</option>
              <option value="Europe/London">London (GMT)</option>
              <option value="Asia/Kolkata">India (IST)</option>
              <option value="Asia/Tokyo">Tokyo (JST)</option>
            </select>
          </div>
        </div>
      </SettingsCard>

      {/* Danger Zone */}
      <SettingsCard className="border-2 !border-red-100">
        <SectionTitle title="Danger Zone" />
        <div className="flex items-start gap-4 p-5 bg-red-50/60 rounded-xl">
          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="font-medium text-gray-900">Delete Account</p>
            <p className="text-sm text-gray-500 mt-1">
              Once you delete your account, all data will be permanently removed. This action cannot be undone.
            </p>
          </div>
          <button
            onClick={() => setDeleteModal(true)}
            className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors shrink-0"
          >
            Delete
          </button>
        </div>
      </SettingsCard>

      <ConfirmModal
        open={deleteModal}
        onClose={() => setDeleteModal(false)}
        onConfirm={() => toast.success("Account deletion requested", { description: "You will receive a confirmation email." })}
        title="Delete your account?"
        description="All of your data, analytics history, and team connections will be permanently deleted. This cannot be undone."
        confirmLabel="Delete Account"
        danger
      />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   3. NOTIFICATIONS TAB
   ═══════════════════════════════════════════════════════════════ */

function NotificationsTab() {
  const [prefs, setPrefs] = useState({
    orderUpdates: true,
    inventoryAlerts: true,
    revenueReports: false,
    marketingEmails: false,
    criticalAlerts: true,
    customerMessages: true,
    systemUpdates: false,
    weeklyDigest: true,
    aiInsights: true,
  });
  const [frequency, setFrequency] = useState("instant");
  const [quietStart, setQuietStart] = useState("22:00");
  const [quietEnd, setQuietEnd] = useState("08:00");
  const [saving, setSaving] = useState(false);

  const toggle = (key: keyof typeof prefs) => setPrefs((p) => ({ ...p, [key]: !p[key] }));

  const NotifRow = ({ label, desc, field }: { label: string; desc: string; field: keyof typeof prefs }) => (
    <div className="flex items-center justify-between py-3.5 border-b border-gray-50 last:border-b-0">
      <div>
        <p className="font-medium text-gray-900 text-sm">{label}</p>
        <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
      </div>
      <Toggle enabled={prefs[field]} onChange={() => toggle(field)} />
    </div>
  );

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("Notification preferences saved");
    }, 600);
  };

  return (
    <div className="space-y-6">
      <SettingsCard>
        <SectionTitle title="Notification Preferences" subtitle="Choose which notifications you'd like to receive" />

        {/* Email */}
        <div className="mb-8">
          <h3 className="font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <Mail className="w-5 h-5 text-purple-600" /> Email Notifications
          </h3>
          <div className="ml-7 mt-3">
            <NotifRow label="Order updates" desc="New orders, fulfillment & delivery updates" field="orderUpdates" />
            <NotifRow label="Inventory alerts" desc="Low stock and out-of-stock warnings" field="inventoryAlerts" />
            <NotifRow label="Revenue reports" desc="Daily and weekly revenue summaries" field="revenueReports" />
            <NotifRow label="Marketing emails" desc="Tips, promotions, and product updates" field="marketingEmails" />
            <NotifRow label="AI Insights" desc="Automated analytics insights and anomalies" field="aiInsights" />
          </div>
        </div>

        {/* Push */}
        <div className="mb-8">
          <h3 className="font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-purple-600" /> Push Notifications
          </h3>
          <div className="ml-7 mt-3">
            <NotifRow label="Critical alerts" desc="Urgent issues requiring immediate attention" field="criticalAlerts" />
            <NotifRow label="Customer messages" desc="New customer inquiries and support tickets" field="customerMessages" />
            <NotifRow label="System updates" desc="Platform updates and maintenance notices" field="systemUpdates" />
            <NotifRow label="Weekly digest" desc="Weekly summary of all store activity" field="weeklyDigest" />
          </div>
        </div>

        {/* Frequency */}
        <div className="mb-6">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Clock className="w-5 h-5 text-purple-600" /> Delivery Frequency
          </h3>
          <div className="grid grid-cols-3 gap-3 ml-7">
            {[
              { id: "instant", label: "Instant", desc: "As they happen" },
              { id: "daily", label: "Daily Digest", desc: "Once a day" },
              { id: "weekly", label: "Weekly Summary", desc: "Once a week" },
            ].map((opt) => (
              <button
                key={opt.id}
                onClick={() => setFrequency(opt.id)}
                className={`p-4 rounded-xl border-2 text-left transition-all ${
                  frequency === opt.id
                    ? "border-purple-500 bg-purple-50"
                    : "border-gray-200 hover:border-purple-200"
                }`}
              >
                <p className="font-medium text-gray-900 text-sm">{opt.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{opt.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Quiet Hours */}
        <div className="mb-2">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Moon className="w-5 h-5 text-purple-600" /> Quiet Hours
          </h3>
          <div className="flex items-center gap-4 ml-7">
            <div>
              <FieldLabel>From</FieldLabel>
              <input type="time" value={quietStart} onChange={(e) => setQuietStart(e.target.value)} className={inputClass + " w-36"} />
            </div>
            <span className="mt-6 text-gray-400">—</span>
            <div>
              <FieldLabel>To</FieldLabel>
              <input type="time" value={quietEnd} onChange={(e) => setQuietEnd(e.target.value)} className={inputClass + " w-36"} />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2 ml-7">Non-critical notifications are silenced during quiet hours.</p>
        </div>

        <SaveCancelBar onSave={handleSave} onCancel={() => {}} saving={saving} />
      </SettingsCard>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   4. BILLING TAB
   ═══════════════════════════════════════════════════════════════ */

function BillingTab() {
  const [currentPlan, setCurrentPlan] = useState("pro");

  const plans = [
    { id: "free", name: "Free", price: "$0", period: "/month", features: ["500 orders/mo", "Basic analytics", "1 team member", "Email support"], badge: "" },
    { id: "pro", name: "Pro", price: "$99", period: "/month", features: ["10,000 orders/mo", "Advanced analytics", "5 team members", "AI Insights", "Priority support"], badge: "Current" },
    { id: "enterprise", name: "Enterprise", price: "$299", period: "/month", features: ["Unlimited orders", "Custom analytics", "Unlimited team", "AI Strategist", "Dedicated support", "Custom integrations"], badge: "Recommended" },
  ];

  const usageData = [
    { label: "Orders", used: 3247, total: 10000, color: "bg-purple-500" },
    { label: "Storage", used: 2.4, total: 10, unit: "GB", color: "bg-blue-500" },
    { label: "API Calls", used: 45000, total: 100000, color: "bg-indigo-500" },
  ];

  const invoices = [
    { id: "INV-2026-003", date: "Mar 1, 2026", amount: "$99.00", status: "Paid" },
    { id: "INV-2026-002", date: "Feb 1, 2026", amount: "$99.00", status: "Paid" },
    { id: "INV-2026-001", date: "Jan 1, 2026", amount: "$99.00", status: "Paid" },
    { id: "INV-2025-012", date: "Dec 1, 2025", amount: "$99.00", status: "Paid" },
  ];

  return (
    <div className="space-y-6">
      {/* Plan Comparison */}
      <SettingsCard>
        <SectionTitle title="Subscription Plan" subtitle="Choose the plan that best fits your business" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((plan) => {
            const isCurrent = plan.id === currentPlan;
            return (
              <div
                key={plan.id}
                className={`relative p-6 rounded-xl border-2 transition-all ${
                  isCurrent ? "border-purple-500 bg-purple-50/50 shadow-md shadow-purple-100" : "border-gray-200 hover:border-purple-200"
                }`}
              >
                {plan.badge && (
                  <span className={`absolute -top-3 left-4 px-3 py-0.5 text-xs font-semibold rounded-full ${
                    plan.badge === "Current" ? "bg-purple-600 text-white" : "bg-gradient-to-r from-amber-400 to-orange-400 text-white"
                  }`}>
                    {plan.badge}
                  </span>
                )}
                <h3 className="text-lg font-semibold text-gray-900 mt-1">{plan.name}</h3>
                <div className="mt-2 mb-4">
                  <span className="text-3xl font-bold text-gray-900">{plan.price}</span>
                  <span className="text-gray-500 text-sm">{plan.period}</span>
                </div>
                <ul className="space-y-2 mb-6">
                  {plan.features.map((f, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
                      <CheckCircle className="w-4 h-4 text-green-500 shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => {
                    if (!isCurrent) {
                      setCurrentPlan(plan.id);
                      toast.success(`Switched to ${plan.name} plan`);
                    }
                  }}
                  className={`w-full py-2.5 rounded-xl font-medium text-sm transition-all ${
                    isCurrent
                      ? "bg-purple-100 text-purple-700 cursor-default"
                      : "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-sm"
                  }`}
                >
                  {isCurrent ? "Current Plan" : `Upgrade to ${plan.name}`}
                </button>
              </div>
            );
          })}
        </div>
      </SettingsCard>

      {/* Usage */}
      <SettingsCard>
        <SectionTitle title="Usage This Month" />
        <div className="space-y-5">
          {usageData.map((item) => {
            const pct = Math.round((item.used / item.total) * 100);
            return (
              <div key={item.label}>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="font-medium text-gray-700">{item.label}</span>
                  <span className="text-gray-500">
                    {item.unit ? `${item.used} ${item.unit}` : item.used.toLocaleString()} / {item.unit ? `${item.total} ${item.unit}` : item.total.toLocaleString()}
                  </span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full ${item.color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </SettingsCard>

      {/* Payment Method */}
      <SettingsCard>
        <SectionTitle title="Payment Method" />
        <div className="flex items-center justify-between p-5 bg-gradient-to-r from-gray-50 to-blue-50/30 rounded-xl border border-gray-100">
          <div className="flex items-center gap-4">
            <div className="w-14 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center shadow-sm">
              <CreditCard className="w-6 h-6 text-white" />
            </div>
            <div>
              <p className="font-semibold text-gray-900">Visa •••• 4242</p>
              <p className="text-sm text-gray-500">Expires 12/2026</p>
            </div>
          </div>
          <button
            onClick={() => toast.info("Payment method", { description: "Payment form would open here." })}
            className="px-5 py-2 border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium transition-colors text-sm"
          >
            Update Card
          </button>
        </div>
      </SettingsCard>

      {/* Billing History */}
      <SettingsCard>
        <SectionTitle title="Billing History" />
        <div className="space-y-2">
          {invoices.map((inv) => (
            <div key={inv.id} className="flex items-center justify-between p-4 hover:bg-gray-50 rounded-xl transition-colors group">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium text-gray-900 text-sm">{inv.id}</p>
                  <p className="text-xs text-gray-500">{inv.date} • {inv.amount}</p>
                </div>
              </div>
              <button
                onClick={() => toast.success(`Downloading ${inv.id}...`)}
                className="flex items-center gap-1.5 text-purple-600 hover:text-purple-700 font-medium text-sm opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <Download className="w-4 h-4" /> Download
              </button>
            </div>
          ))}
        </div>
      </SettingsCard>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   5. TEAM TAB
   ═══════════════════════════════════════════════════════════════ */

function TeamTab() {
  const [members, setMembers] = useState([
    { id: 1, name: "John Doe", email: "john.doe@company.com", role: "Owner", avatar: "JD", status: "Active" },
    { id: 2, name: "Sarah Smith", email: "sarah.smith@company.com", role: "Admin", avatar: "SS", status: "Active" },
    { id: 3, name: "Mike Johnson", email: "mike.johnson@company.com", role: "Member", avatar: "MJ", status: "Active" },
  ]);
  const [pendingInvites, setPendingInvites] = useState([
    { id: 101, email: "alex.kumar@company.com", role: "Member", sentAt: "2 days ago" },
  ]);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("Member");
  const [removeModal, setRemoveModal] = useState<{ open: boolean; memberId: number | null }>({ open: false, memberId: null });

  const gradients = [
    "from-purple-500 to-indigo-600",
    "from-pink-500 to-rose-600",
    "from-emerald-500 to-teal-600",
    "from-amber-500 to-orange-600",
    "from-cyan-500 to-blue-600",
  ];

  const handleInvite = () => {
    if (!inviteEmail || !inviteEmail.includes("@")) {
      toast.error("Please enter a valid email"); return;
    }
    setPendingInvites((p) => [...p, { id: Date.now(), email: inviteEmail, role: inviteRole, sentAt: "Just now" }]);
    toast.success("Invitation sent", { description: `Invite sent to ${inviteEmail}` });
    setInviteEmail("");
    setShowInvite(false);
  };

  const handleRemove = (id: number) => {
    setMembers((m) => m.filter((x) => x.id !== id));
    toast.success("Member removed");
  };

  const handleRoleChange = (id: number, newRole: string) => {
    setMembers((m) => m.map((x) => (x.id === id ? { ...x, role: newRole } : x)));
    toast.success("Role updated");
  };

  const cancelInvite = (id: number) => {
    setPendingInvites((p) => p.filter((x) => x.id !== id));
    toast.success("Invitation cancelled");
  };

  return (
    <div className="space-y-6">
      <SettingsCard>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Team Members</h2>
            <p className="text-gray-500 mt-1">Manage your team and their permissions</p>
          </div>
          <button
            onClick={() => setShowInvite(true)}
            className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all shadow-md shadow-purple-200 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Invite Member
          </button>
        </div>

        {/* Invite Form */}
        {showInvite && (
          <div className="p-5 bg-purple-50/60 rounded-xl border border-purple-100 mb-6 animate-in fade-in slide-in-from-top-2 duration-200">
            <h3 className="font-semibold text-gray-900 mb-3">Send Invitation</h3>
            <div className="flex gap-3">
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                className={inputClass + " flex-1"}
              />
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} className={inputClass + " w-36"}>
                <option>Admin</option>
                <option>Member</option>
                <option>Viewer</option>
              </select>
              <button onClick={handleInvite} className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-medium transition-colors shrink-0">
                Send
              </button>
              <button onClick={() => setShowInvite(false)} className="px-3 py-2.5 text-gray-500 hover:text-gray-700 transition-colors shrink-0">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {/* Members List */}
        <div className="space-y-2">
          {members.map((member, idx) => (
            <div key={member.id} className="flex items-center justify-between p-4 hover:bg-gray-50 rounded-xl transition-colors group">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 bg-gradient-to-br ${gradients[idx % gradients.length]} rounded-full flex items-center justify-center text-white font-semibold shadow-sm`}>
                  {member.avatar}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900">{member.name}</p>
                    {member.role === "Owner" && (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-medium">Owner</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500">{member.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <select
                  value={member.role}
                  onChange={(e) => handleRoleChange(member.id, e.target.value)}
                  disabled={member.role === "Owner"}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-400 disabled:opacity-50 disabled:cursor-not-allowed bg-white"
                >
                  <option>Owner</option>
                  <option>Admin</option>
                  <option>Member</option>
                  <option>Viewer</option>
                </select>
                {member.role !== "Owner" && (
                  <button
                    onClick={() => setRemoveModal({ open: true, memberId: member.id })}
                    className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </SettingsCard>

      {/* Pending Invitations */}
      {pendingInvites.length > 0 && (
        <SettingsCard>
          <SectionTitle title="Pending Invitations" />
          <div className="space-y-2">
            {pendingInvites.map((invite) => (
              <div key={invite.id} className="flex items-center justify-between p-4 bg-amber-50/50 rounded-xl border border-amber-100">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
                    <Mail className="w-5 h-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{invite.email}</p>
                    <p className="text-xs text-gray-500">{invite.role} • Sent {invite.sentAt}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { cancelInvite(invite.id); }}
                    className="px-3 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-sm font-medium transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => toast.success("Invitation resent")}
                    className="px-3 py-1.5 text-purple-600 hover:bg-purple-50 rounded-lg text-sm font-medium transition-colors"
                  >
                    Resend
                  </button>
                </div>
              </div>
            ))}
          </div>
        </SettingsCard>
      )}

      <ConfirmModal
        open={removeModal.open}
        onClose={() => setRemoveModal({ open: false, memberId: null })}
        onConfirm={() => removeModal.memberId && handleRemove(removeModal.memberId)}
        title="Remove team member?"
        description="This person will lose access to all team resources immediately."
        confirmLabel="Remove"
        danger
      />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   6. INTEGRATIONS TAB
   ═══════════════════════════════════════════════════════════════ */

function IntegrationsTab() {
  const [integrations, setIntegrations] = useState([
    { id: "shopify", name: "Shopify", description: "E-commerce platform integration", connected: true, icon: "🛍️", category: "Commerce" },
    { id: "stripe", name: "Stripe", description: "Payment processing and invoicing", connected: true, icon: "💳", category: "Payments" },
    { id: "razorpay", name: "Razorpay", description: "India payment gateway", connected: false, icon: "🏦", category: "Payments" },
    { id: "slack", name: "Slack", description: "Team communication and alerts", connected: false, icon: "💬", category: "Communication" },
    { id: "mailchimp", name: "Mailchimp", description: "Email marketing campaigns", connected: false, icon: "📧", category: "Marketing" },
    { id: "ga", name: "Google Analytics", description: "Website traffic and conversion data", connected: true, icon: "📊", category: "Analytics" },
    { id: "meta", name: "Meta Ads", description: "Facebook & Instagram ad performance", connected: false, icon: "📱", category: "Marketing" },
    { id: "zapier", name: "Zapier", description: "Automate workflows across apps", connected: false, icon: "⚡", category: "Automation" },
  ]);

  const [webhookUrl] = useState("https://api.commercepulse.com/webhooks/v1/abc123xyz");
  const [copied, setCopied] = useState(false);

  const toggleConnection = (id: string) => {
    setIntegrations((prev) =>
      prev.map((i) => {
        if (i.id === id) {
          const next = !i.connected;
          toast.success(next ? `${i.name} connected` : `${i.name} disconnected`);
          return { ...i, connected: next };
        }
        return i;
      })
    );
  };

  const copyWebhook = () => {
    navigator.clipboard.writeText(webhookUrl);
    setCopied(true);
    toast.success("Webhook URL copied");
    setTimeout(() => setCopied(false), 2000);
  };

  const categories = [...new Set(integrations.map((i) => i.category))];

  return (
    <div className="space-y-6">
      {categories.map((cat) => (
        <SettingsCard key={cat}>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{cat}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {integrations
              .filter((i) => i.category === cat)
              .map((integration) => (
                <div
                  key={integration.id}
                  className={`p-5 border-2 rounded-xl transition-all ${
                    integration.connected ? "border-green-200 bg-green-50/30" : "border-gray-200 hover:border-purple-200"
                  }`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">{integration.icon}</span>
                      <div>
                        <h4 className="font-semibold text-gray-900">{integration.name}</h4>
                        <p className="text-xs text-gray-500 mt-0.5">{integration.description}</p>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => toggleConnection(integration.id)}
                    className={`w-full py-2.5 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2 ${
                      integration.connected
                        ? "bg-green-100 text-green-700 border border-green-200 hover:bg-red-50 hover:text-red-600 hover:border-red-200"
                        : "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white shadow-sm"
                    }`}
                  >
                    {integration.connected ? (
                      <><CheckCircle className="w-4 h-4" /> Connected</>
                    ) : (
                      <><ExternalLink className="w-4 h-4" /> Connect</>
                    )}
                  </button>
                </div>
              ))}
          </div>
        </SettingsCard>
      ))}

      {/* Webhook URL */}
      <SettingsCard>
        <SectionTitle title="Webhook URL" subtitle="Use this URL to receive real-time event notifications" />
        <div className="flex items-center gap-3">
          <div className="flex-1 px-4 py-3 bg-gray-50 rounded-xl font-mono text-sm text-gray-600 border border-gray-200 truncate">
            {webhookUrl}
          </div>
          <button
            onClick={copyWebhook}
            className="px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-colors shrink-0"
          >
            {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
          </button>
        </div>
      </SettingsCard>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   7. APPEARANCE TAB
   ═══════════════════════════════════════════════════════════════ */

function AppearanceTab() {
  const [theme, setTheme] = useState<"light" | "dark" | "auto">("light");
  const [accent, setAccent] = useState(0);
  const [fontSize, setFontSize] = useState<"small" | "default" | "large">("default");
  const [density, setDensity] = useState<"compact" | "comfortable" | "spacious">("comfortable");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [saving, setSaving] = useState(false);

  const accentColors = [
    { name: "Purple", bg: "bg-purple-600", ring: "ring-purple-300" },
    { name: "Blue", bg: "bg-blue-600", ring: "ring-blue-300" },
    { name: "Emerald", bg: "bg-emerald-600", ring: "ring-emerald-300" },
    { name: "Rose", bg: "bg-rose-600", ring: "ring-rose-300" },
    { name: "Amber", bg: "bg-amber-500", ring: "ring-amber-300" },
    { name: "Cyan", bg: "bg-cyan-600", ring: "ring-cyan-300" },
  ];

  const themes = [
    { id: "light" as const, label: "Light", icon: Sun, preview: "bg-white border-gray-200" },
    { id: "dark" as const, label: "Dark", icon: Moon, preview: "bg-gray-900 border-gray-700" },
    { id: "auto" as const, label: "System", icon: Monitor, preview: "bg-gradient-to-r from-white to-gray-900 border-gray-300" },
  ];

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("Appearance settings saved");
    }, 600);
  };

  return (
    <div className="space-y-6">
      {/* Theme */}
      <SettingsCard>
        <SectionTitle title="Theme" subtitle="Customize how CommercePulse looks" />
        <div className="grid grid-cols-3 gap-4">
          {themes.map((t) => {
            const Icon = t.icon;
            const active = theme === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTheme(t.id)}
                className={`p-5 border-2 rounded-xl transition-all ${
                  active ? "border-purple-500 bg-purple-50/50 shadow-md shadow-purple-100" : "border-gray-200 hover:border-purple-200"
                }`}
              >
                <div className={`w-full h-16 rounded-lg mb-3 border ${t.preview}`} />
                <div className="flex items-center justify-center gap-2">
                  <Icon className={`w-4 h-4 ${active ? "text-purple-600" : "text-gray-500"}`} />
                  <p className={`font-medium text-sm ${active ? "text-purple-700" : "text-gray-700"}`}>{t.label}</p>
                </div>
              </button>
            );
          })}
        </div>
      </SettingsCard>

      {/* Accent Color */}
      <SettingsCard>
        <SectionTitle title="Accent Color" subtitle="Choose your preferred brand color" />
        <div className="flex gap-3 flex-wrap">
          {accentColors.map((color, idx) => (
            <button
              key={idx}
              onClick={() => { setAccent(idx); toast.success(`Accent color set to ${color.name}`); }}
              className={`w-12 h-12 ${color.bg} rounded-xl transition-all hover:scale-110 ${
                accent === idx ? `ring-4 ${color.ring} scale-110` : ""
              }`}
              title={color.name}
            />
          ))}
        </div>
      </SettingsCard>

      {/* Font Size & Density */}
      <SettingsCard>
        <SectionTitle title="Display" subtitle="Adjust font size and information density" />

        {/* Font Size */}
        <div className="mb-6">
          <FieldLabel>Font Size</FieldLabel>
          <div className="grid grid-cols-3 gap-3">
            {(["small", "default", "large"] as const).map((size) => (
              <button
                key={size}
                onClick={() => setFontSize(size)}
                className={`p-4 border-2 rounded-xl transition-all text-center ${
                  fontSize === size ? "border-purple-500 bg-purple-50" : "border-gray-200 hover:border-purple-200"
                }`}
              >
                <span className={`font-medium ${size === "small" ? "text-xs" : size === "large" ? "text-lg" : "text-sm"} text-gray-900`}>
                  Aa
                </span>
                <p className="text-xs text-gray-500 mt-1 capitalize">{size}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Density */}
        <div className="mb-6">
          <FieldLabel>Information Density</FieldLabel>
          <div className="grid grid-cols-3 gap-3">
            {(["compact", "comfortable", "spacious"] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDensity(d)}
                className={`p-4 border-2 rounded-xl transition-all ${
                  density === d ? "border-purple-500 bg-purple-50" : "border-gray-200 hover:border-purple-200"
                }`}
              >
                <div className="flex flex-col items-center gap-1 mb-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className={`bg-gray-300 rounded-full ${
                        d === "compact" ? "h-1 w-8" : d === "spacious" ? "h-2 w-10" : "h-1.5 w-9"
                      }`}
                    />
                  ))}
                </div>
                <p className="text-xs text-gray-500 capitalize">{d}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div className="flex items-center justify-between py-4 border-t border-gray-100">
          <div>
            <p className="font-medium text-gray-900 text-sm">Collapse sidebar by default</p>
            <p className="text-xs text-gray-500 mt-0.5">Start with a minimized sidebar to maximize content area</p>
          </div>
          <Toggle enabled={sidebarCollapsed} onChange={setSidebarCollapsed} />
        </div>

        <SaveCancelBar onSave={handleSave} onCancel={() => {}} saving={saving} />
      </SettingsCard>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   8. SECURITY TAB
   ═══════════════════════════════════════════════════════════════ */

function SecurityTab() {
  const [twoFAEnabled, setTwoFAEnabled] = useState(true);
  const [apiKeys, setApiKeys] = useState([
    { id: 1, name: "Production Key", key: "sk_live_••••••••••••4242", created: "Jan 15, 2026", lastUsed: "2 hours ago" },
    { id: 2, name: "Development Key", key: "sk_test_••••••••••••8888", created: "Mar 1, 2026", lastUsed: "5 mins ago" },
  ]);
  const [sessions, setSessions] = useState([
    { id: 1, device: "Windows PC — Chrome", location: "Hyderabad, IN", time: "Active now", current: true },
    { id: 2, device: "iPhone 14 Pro — Safari", location: "Hyderabad, IN", time: "2 hours ago", current: false },
    { id: 3, device: "MacBook Pro — Firefox", location: "Mumbai, IN", time: "3 days ago", current: false },
  ]);
  const [showNewKey, setShowNewKey] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [generatedKey, setGeneratedKey] = useState("");
  const [revokeModal, setRevokeModal] = useState<{ open: boolean; keyId: number | null }>({ open: false, keyId: null });
  const [revokeSessionModal, setRevokeSessionModal] = useState<{ open: boolean; sessionId: number | null }>({ open: false, sessionId: null });
  const [copiedKey, setCopiedKey] = useState(false);

  const generateApiKey = () => {
    if (!newKeyName.trim()) { toast.error("Please enter a key name"); return; }
    const key = `sk_live_${Array.from({ length: 32 }, () => "abcdefghijklmnopqrstuvwxyz0123456789"[Math.floor(Math.random() * 36)]).join("")}`;
    setGeneratedKey(key);
  };

  const saveNewKey = () => {
    setApiKeys((prev) => [
      ...prev,
      { id: Date.now(), name: newKeyName, key: `sk_live_••••••••••••${generatedKey.slice(-4)}`, created: "Just now", lastUsed: "Never" },
    ]);
    toast.success("API key created", { description: "Make sure to copy it — you won't see it again." });
    setShowNewKey(false);
    setNewKeyName("");
    setGeneratedKey("");
  };

  const revokeKey = (id: number) => {
    setApiKeys((prev) => prev.filter((k) => k.id !== id));
    toast.success("API key revoked");
  };

  const revokeSession = (id: number) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    toast.success("Session revoked");
  };

  const copyKey = () => {
    navigator.clipboard.writeText(generatedKey);
    setCopiedKey(true);
    toast.success("API key copied to clipboard");
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Two-Factor Auth */}
      <SettingsCard>
        <div className="flex items-start justify-between">
          <div>
            <SectionTitle title="Two-Factor Authentication" subtitle="Add an extra layer of security to your account" />
          </div>
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium ${twoFAEnabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
              {twoFAEnabled ? <CheckCircle className="w-4 h-4" /> : <X className="w-4 h-4" />}
              {twoFAEnabled ? "Enabled" : "Disabled"}
            </div>
            <Toggle
              enabled={twoFAEnabled}
              onChange={(v) => {
                setTwoFAEnabled(v);
                toast.success(v ? "2FA enabled" : "2FA disabled", {
                  description: v ? "Your account is now more secure." : "Two-factor authentication has been turned off.",
                });
              }}
            />
          </div>
        </div>
        {twoFAEnabled && (
          <div className="mt-4 p-4 bg-green-50/60 border border-green-100 rounded-xl">
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-green-600" />
              <div>
                <p className="text-sm font-medium text-green-800">Two-factor authentication is active</p>
                <p className="text-xs text-green-600 mt-0.5">Using authenticator app. Last verified 2 hours ago.</p>
              </div>
            </div>
          </div>
        )}
      </SettingsCard>

      {/* API Keys */}
      <SettingsCard>
        <div className="flex items-center justify-between mb-6">
          <SectionTitle title="API Keys" subtitle="Manage keys for external integrations" />
          <button
            onClick={() => setShowNewKey(true)}
            className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all shadow-md shadow-purple-200 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Generate Key
          </button>
        </div>

        {/* New Key Form */}
        {showNewKey && (
          <div className="p-5 bg-purple-50/60 rounded-xl border border-purple-100 mb-6 animate-in fade-in slide-in-from-top-2 duration-200">
            <h3 className="font-semibold text-gray-900 mb-3">Generate New API Key</h3>
            {!generatedKey ? (
              <div className="flex gap-3">
                <input
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="Key name (e.g., Staging)"
                  className={inputClass + " flex-1"}
                />
                <button onClick={generateApiKey} className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-medium transition-colors shrink-0 flex items-center gap-2">
                  <Zap className="w-4 h-4" /> Generate
                </button>
                <button onClick={() => { setShowNewKey(false); setNewKeyName(""); }} className="px-3 text-gray-500 hover:text-gray-700">
                  <X className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  <p className="text-sm text-amber-700 font-medium">Copy this key now. You won't be able to see it again.</p>
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-4 py-3 bg-gray-900 text-green-400 rounded-xl font-mono text-sm truncate">
                    {generatedKey}
                  </code>
                  <button onClick={copyKey} className="p-3 bg-gray-800 hover:bg-gray-700 text-white rounded-xl transition-colors">
                    {copiedKey ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                  </button>
                </div>
                <div className="flex justify-end gap-3">
                  <button onClick={() => { setShowNewKey(false); setNewKeyName(""); setGeneratedKey(""); }} className="px-4 py-2 text-gray-600 hover:bg-gray-50 rounded-xl font-medium">
                    Cancel
                  </button>
                  <button onClick={saveNewKey} className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-medium transition-colors">
                    Save Key
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Key List */}
        <div className="space-y-2">
          {apiKeys.map((apiKey) => (
            <div key={apiKey.id} className="flex items-center justify-between p-4 bg-gray-50/80 rounded-xl hover:bg-gray-50 transition-colors group">
              <div className="flex items-center gap-3">
                <Key className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="font-medium text-gray-900 text-sm">{apiKey.name}</p>
                  <p className="text-xs text-gray-500 font-mono">{apiKey.key}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <p className="text-xs text-gray-400 hidden sm:block">Created {apiKey.created} • Last used {apiKey.lastUsed}</p>
                <button
                  onClick={() => setRevokeModal({ open: true, keyId: apiKey.id })}
                  className="text-red-500 hover:text-red-700 font-medium text-sm opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  Revoke
                </button>
              </div>
            </div>
          ))}
        </div>
      </SettingsCard>

      {/* Active Sessions */}
      <SettingsCard>
        <SectionTitle title="Active Sessions" subtitle="Manage devices logged into your account" />
        <div className="space-y-2">
          {sessions.map((session) => (
            <div key={session.id} className="flex items-center justify-between p-4 hover:bg-gray-50 rounded-xl transition-colors group">
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${session.current ? "bg-green-100" : "bg-gray-100"}`}>
                  <Monitor className={`w-5 h-5 ${session.current ? "text-green-600" : "text-gray-500"}`} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900 text-sm">{session.device}</p>
                    {session.current && (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">This device</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 flex items-center gap-1.5 mt-0.5">
                    <MapPin className="w-3 h-3" /> {session.location} • <Clock className="w-3 h-3" /> {session.time}
                  </p>
                </div>
              </div>
              {!session.current && (
                <button
                  onClick={() => setRevokeSessionModal({ open: true, sessionId: session.id })}
                  className="text-red-500 hover:text-red-700 font-medium text-sm opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  Revoke
                </button>
              )}
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-gray-100">
          <button
            onClick={() => {
              setSessions((prev) => prev.filter((s) => s.current));
              toast.success("All other sessions revoked");
            }}
            className="text-red-600 hover:text-red-700 font-medium text-sm"
          >
            Revoke all other sessions
          </button>
        </div>
      </SettingsCard>

      {/* Modals */}
      <ConfirmModal
        open={revokeModal.open}
        onClose={() => setRevokeModal({ open: false, keyId: null })}
        onConfirm={() => revokeModal.keyId && revokeKey(revokeModal.keyId)}
        title="Revoke API key?"
        description="Any integrations using this key will immediately lose access. This cannot be undone."
        confirmLabel="Revoke Key"
        danger
      />
      <ConfirmModal
        open={revokeSessionModal.open}
        onClose={() => setRevokeSessionModal({ open: false, sessionId: null })}
        onConfirm={() => revokeSessionModal.sessionId && revokeSession(revokeSessionModal.sessionId)}
        title="Revoke session?"
        description="This device will be logged out immediately."
        confirmLabel="Revoke Session"
        danger
      />
    </div>
  );
}
