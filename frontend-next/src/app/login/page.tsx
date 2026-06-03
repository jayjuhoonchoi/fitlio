import Link from "next/link";

import { LoginForm } from "@/components/molecules/login-form";
import { centerConfig } from "@/lib/center";

export default function MemberLoginPage(): JSX.Element {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-6 py-12">
      <LoginForm
        mode="member"
        title="Member sign in"
        subtitle={`Access ${centerConfig.name} booking and check-in.`}
      />
      <p className="mt-6 text-center text-sm text-muted">
        <Link href="/" className="text-accent hover:underline">
          Back to home
        </Link>
        {" · "}
        <Link href="/admin-login" className="text-silver hover:text-text">
          Admin
        </Link>
      </p>
    </div>
  );
}
