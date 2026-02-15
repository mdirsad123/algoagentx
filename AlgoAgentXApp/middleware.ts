import { createI18nMiddleware } from "next-international/middleware";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const supportedLocales = ["en", "hi", "fr", "ar"];

const PUBLIC_PATHS = new Set([
  "/auth/login",
  "/auth/signup",
  "/auth/forgotpassword",
]);

const I18nMiddleware = createI18nMiddleware({
  locales: supportedLocales,
  defaultLocale: "en",
  urlMappingStrategy: "rewrite",
});


const getNormalizedPath = (path: string): string => {
  const pathSegments = path.split("/");
  if (supportedLocales.includes(pathSegments[1])) {
    return `/${pathSegments.slice(2).join("/")}`;
  }
  return path;
};

const isAuthenticated = (request: NextRequest): boolean => {
  // Check for token in cookies (set by client-side JavaScript after login)
  const token = request.cookies.get("accessToken")?.value;
  return !!token;
};

export async function middleware(request: NextRequest) {
  const response = I18nMiddleware(request); // Apply i18n middleware first
  const rawPath = request.nextUrl.pathname;
  const normalizedPath = getNormalizedPath(rawPath);

  // console.log("Raw Path:", rawPath);
  // console.log("Normalized Path:", normalizedPath);

  // Allow access to public paths without authentication
  if (PUBLIC_PATHS.has(normalizedPath) || normalizedPath === "/") {
    return response;
  }

  // Redirect unauthenticated users
  if (!isAuthenticated(request)) {
    // console.log("Not Authenticated");
    const loginUrl = new URL("/auth/login", request.url);
    loginUrl.searchParams.set("redirect", normalizedPath);
    return NextResponse.redirect(loginUrl);
  }

// TEMPORARILY DISABLE ROLE-BASED ACCESS CONTROL
// TODO: Re-enable after stabilizing the application
/*
const roleId = request.cookies.get("loggedinuserroleid")?.value;

  if (roleId) {
    const rolePermissions: Record<string, string[]> = {
      "1": ["home/dashboard_systemadmin","company","master","spare","vehicle","company","courttype","courtmaster","casestatus","casestage","stafftype","supplier","category","driver","userconfig","transaction","myprofile","changepassword","auth/otp","notifications"],
      "2": ["home/dashboard_systemadmin","company","master","courttype","courtmaster","casestatus","casestage","stafftype","supplier","category","driver","userconfig","transaction","myprofile","changepassword","auth/otp","notifications"],
      "3": ["home/dashboard_admin","casemanagement","case","contact/assignedunassignedtoclient","assigned_unassigned_clients","invoice","invoicecancellation","receiptentry","receiptcancel","ledger","casesceduler","billspayments","bills","paymentsreceipts",
        "reports","casereport","casedatereport","caseorderreport","causelistreportautomated","causelistposreportautomated","contact","client","parties","lawfirm","courtmaster","judge","advocate","employee","userconfig","usermaster","myprofile/","companydetails/","changepassword","auth/otp","calendar","notifications"],
      "4": ["home/dashboard_employee","home/dashboard_employee/clientdetails","casemanagement","case","calendar","casesceduler","billspayments","bills","invoice","invoicecancellation","paymentsreceipts","reports","casereport","casedatereport","caseorderreport","causelistreportautomated","causelistposreportautomated","myprofile","companydetails/","changepassword","auth/otp","notifications"],
      "5": ["home/dashboard_advocate","home/dashboard_advocate/clientdetails","casemanagement","case","billspayments","bills","invoice","invoicecancellation","paymentsreceipts","reports","casereport","casedatereport","caseorderreport","/calendar","causelistreportautomated","causelistposreportautomated","myprofile","auth/otp","changepassword","companydetails/","notifications"],
      "6": ["home/dashboard_client","home/dashboard_client/clientdetails","casemanagement","case","casedates","billspayments","bills","paymentsreceipts","reports","casereport","casedatereport","caseorderreport","causelistreportautomated","causelistposreportautomated","myprofile","changepassword","companydetails/","auth/otp","notifications","uploadfiles"],
      "7": ["home","casemanagement","case","casedates","casesceduler","billspayments","bills","paymentsreceipts","reports","casereport","casedatereport","caseorderreport","causelistreportautomated","causelistposreportautomated","myprofile","auth/otp","notifications"],
    };

    const allowedFeatures = rolePermissions[roleId] || [];

    // Check if any allowed feature is a prefix of the path
    const hasAccess = allowedFeatures.some(feature => normalizedPath.startsWith(`/${feature}`));

    if (!hasAccess) {
      return NextResponse.rewrite(new URL("/404", request.url));
    }
  }
*/

    return response;
  }

// Middleware configuration
export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|robots.txt|.*\\.(?:jpg|jpeg|png|gif|svg|webp)).*)",
  ],
};
