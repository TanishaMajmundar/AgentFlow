import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, Lock, Mail } from "lucide-react";
import AuthLayout from "../components/layouts/AuthLayout";
import Field from "../components/Field";
import PasswordToggle from "../components/PasswordToggle";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../api/client";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");

  if (user) return <Navigate to="/projects" replace />;

  const set = (k) => (e) => { setForm({ ...form, [k]: e.target.value }); setErrors({ ...errors, [k]: undefined }); };

  const validate = () => {
    const e = {};
    if (!EMAIL_RE.test(form.email)) e.email = "Enter a valid email address.";
    if (!form.password) e.password = "Enter your password.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    if (!validate()) return;
    setLoading(true); setFormError("");
    try {
      await login(form);
      navigate(location.state?.from || "/projects", { replace: true });
    } catch (err) {
      setFormError(getErrorMessage(err));
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to pick up where your agents left off."
      footer={<>New to AgentFlow?{" "}<Link to="/signup" className="font-medium text-brand hover:underline">Create an account</Link></>}
    >
      <form className="stagger mt-8 flex flex-col gap-4" onSubmit={submit} noValidate>
        <Field id="email" icon={Mail} type="email" autoComplete="email" placeholder="you@university.edu"
          value={form.email} onChange={set("email")} error={errors.email} />
        <Field id="password" icon={Lock} type={showPw ? "text" : "password"} autoComplete="current-password" placeholder="Password"
          value={form.password} onChange={set("password")} error={errors.password}
          right={<PasswordToggle shown={showPw} onToggle={() => setShowPw((s) => !s)} />} />

        <div className="-mt-1 flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-muted">
            <input type="checkbox" className="accent-brand" /> Remember me
          </label>
          <button type="button" className="text-xs text-muted transition hover:text-ink">Forgot password?</button>
        </div>

        {formError && <p role="alert" className="text-sm text-danger">{formError}</p>}

        <button className="btn-primary mt-2 !py-3" disabled={loading}>
          {loading ? "Logging in…" : <>Log in <ArrowRight size={15} className="nudge" /></>}
        </button>
      </form>
    </AuthLayout>
  );
}
