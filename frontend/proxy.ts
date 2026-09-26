import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const publicPath = request.nextUrl.pathname === "/login";
  const signedIn = request.cookies.has("article_publisher_session");
  if (!signedIn && !publicPath) return NextResponse.redirect(new URL("/login", request.url));
  if (signedIn && publicPath) return NextResponse.redirect(new URL("/dashboard", request.url));
  return NextResponse.next();
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
