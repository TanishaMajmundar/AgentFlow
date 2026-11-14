import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, Lock, Mail, User } from "lucide-react";
import AuthLayout from "../components/layouts/AuthLayout";
import Field from "../components/Field";
import PasswordToggle from "../components/PasswordToggle";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../api/client";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Signup() {
  const { user, signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "", terms: false });
  const [errors, setErrors] = useState({});
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");

  if (user) return <Navigate to="/projects" replace />;

  const set = (k) => (e) => {
    const v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm({ ...form, [k]: v }); setErrors({ ...errors, [k]: undefined });
  };

  const validate = () => {
    const e = {};
    if (form.name.trim().length < 2) e.name = "Enter your full name.";
    if (!EMAIL_RE.test(form.email)) e.email = "Enter a valid email address.";
    if (form.password.length < 8) e.password = "Use at least 8 characters.";
    if (form.confirm !== form.password) e.confirm = "Passwords don't match.";
    if (!form.terms) e.terms = "Please accept the terms to continue.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    if (!validate()) return;
    setLoading(true); setFormError("");
    try {
      await signup(form);
      navigate("/projects", { replace: true });
    } catch (err) {
      setFormError(getErrorMessage(err));
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Set up your workspace and start your first project."
      footer={<>Already have an account?{" "}<Link to="/login" className="font-medium text-brand hover:underline">Log in</Link></>}
    >
      <form className="stagger mt-8 flex flex-col gap-4" onSubmit={submit} noValidate>
        <Field id="name" icon={User} autoComplete="name" placeholder="Full name"
          value={form.name} onChange={set("name")} error={errors.name} />
        <Field id="email" icon={Mail} type="email" autoComplete="email" placeholder="you@university.edu"
          value={form.email} onChange={set("email")} error={errors.email} />
        <Field id="password" icon={Lock} type={showPw ? "text" : "password"} autoComplete="new-password" placeholder="Create a password"
          value={form.password} onChange={set("password")} error={errors.password}
          right={<PasswordToggle shown={showPw} onToggle={() => setShowPw((s) => !s)} />} />
        <Field id="confirm" icon={Lock} type={showPw ? "text" : "password"} autoComplete="new-password" placeholder="Confirm password"
          value={form.confirm} onChange={set("confirm")} error={errors.confirm} />

        <div className="-mt-1">
          <label className="flex items-start gap-2 text-xs text-muted">
            <input type="checkbox" className="mt-0.5 accent-brand" checked={form.terms} onChange={set("terms")} />
            I agree to the Terms of Service and Privacy Policy
          </label>
          {errors.terms && <p role="alert" className="mt-1.5 text-xs text-danger">{errors.terms}</p>}
        </div>

        {formError && <p role="alert" className="text-sm text-danger">{formError}</p>}

        <button className="btn-primary mt-2 !py-3" disabled={loading}>
          {loading ? "Creating account…" : <>Create account <ArrowRight size={15} className="nudge" /></>}
        </button>
      </form>
    </AuthLayout>
  );
}
