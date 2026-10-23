import { reportBff } from "../../../../lib/report-bff";
import { reportQuery, reportsPath } from "../../../../lib/reports-security";

export const GET = reportBff(reportsPath, reportQuery);
export const POST = GET;
