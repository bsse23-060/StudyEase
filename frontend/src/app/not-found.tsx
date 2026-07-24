import Link from "next/link";
export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <div className="text-center">
        <p className="text-sm font-bold text-emerald-800">404</p>
        <h1 className="text-3xl font-black">We couldn’t find that page</h1>
        <Link className="mt-5 inline-block underline" href="/dashboard">
          Return to dashboard
        </Link>
      </div>
    </main>
  );
}
