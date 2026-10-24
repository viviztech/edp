import { NextRequest } from "next/server";
import { cmsFileTransport } from "../../../../lib/cms-file-transport";
import { settings } from "../../../../lib/server-api";

export async function GET(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const parts = (await context.params).path;
  const id = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
  if (!new RegExp(`^organizations/${id}/assets/${id}/content$`).test(parts.join("/")) || request.nextUrl.search) return Response.json({error:{code:"not_found"}},{status:404,headers:{"Cache-Control":"no-store"}});
  try {
    return await cmsFileTransport(request,settings().api+"/api/v1/public/"+parts.join("/"),{},parts[3],true);
  } catch {
    return Response.json({error:{code:"service_unavailable"}},{status:503,headers:{"Cache-Control":"no-store"}});
  }
}
