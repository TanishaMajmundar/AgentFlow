import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <p className="font-mono text-sm text-brand">404</p>
      <h1 className="mt-2 font-display text-3xl font-semibold">This page wandered off</h1>
      <p className="mt-2 max-w-sm text-sm text-muted">
        The agent that was supposed to deliver it never reported back.
      </p>
      <Link to="/" className="btn-primary mt-7">Back to home</Link>
    </main>
  );
}
