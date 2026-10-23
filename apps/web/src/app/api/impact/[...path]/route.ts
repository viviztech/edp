import { reportBff } from "../../../../lib/report-bff";
import { impactPath, impactQuery } from "../../../../lib/impact-security";

export const GET = reportBff(impactPath, impactQuery);
export const POST = GET;
