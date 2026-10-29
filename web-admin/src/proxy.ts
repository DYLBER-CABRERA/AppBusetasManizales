import { NextResponse, type NextRequest } from "next/server";

// Next 16 renombró middleware.ts a proxy.ts. Aquí solo se exige que exista sesión (cookie de Supabase);
// el rol lo valida el backend (GET /yo) y lo aplica el layout `(panel)` en el cliente.
export function proxy(req: NextRequest) {
  const hayCookieSupabase = req.cookies.getAll().some((c) => /^sb-.*-auth-token/.test(c.name));
  if (hayCookieSupabase) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  return NextResponse.redirect(url);
}

export const config = { matcher: ["/jefe/:path*", "/secretaria/:path*", "/admin/:path*"] };
