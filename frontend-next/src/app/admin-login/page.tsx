import Link from "next/link";

import { LoginForm } from "@/components/molecules/login-form";
import { centerConfig } from "@/lib/center";

export default function AdminLoginPage(): JSX.Element {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-6 py-12">
      <LoginForm
        mode="admin"
        title="Admin sign in"
        subtitle={`Staff console for ${centerConfig.name}.`}
      />
      <p className="mt-6 text-center text-sm text-muted">
        <Link href="/" className="text-accent hover:underline">
          Back to home
        </Link>
        {" · "}
        <Link href="/login" className="text-silver hover:text-text">
          Member
        </Link>
      </p>
    </div>
  );
}
