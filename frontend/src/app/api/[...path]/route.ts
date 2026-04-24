import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, params: Promise<{ path: string[] }>) {
  const { path } = await params;
  const url = new URL(request.url);
  const backendUrl = `${BACKEND}/${path.join("/")}${url.search}`;

  const headers = new Headers();
  const ct = request.headers.get("content-type");
  if (ct) headers.set("content-type", ct);

  const body = request.method !== "GET" && request.method !== "HEAD"
    ? await request.text()
    : undefined;

  const res = await fetch(backendUrl, {
    method: request.method,
    headers,
    body,
  });

  const data = await res.text();

  return new NextResponse(data, {
    status: res.status,
    headers: {
      "content-type": res.headers.get("content-type") ?? "application/json",
    },
  });
}

export const GET     = (req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) => proxy(req, ctx.params);
export const POST    = (req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) => proxy(req, ctx.params);
export const PUT     = (req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) => proxy(req, ctx.params);
export const DELETE  = (req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) => proxy(req, ctx.params);
export const PATCH   = (req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) => proxy(req, ctx.params);
