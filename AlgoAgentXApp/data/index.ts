import { Building2, CreditCard, HandCoinsIcon, Handshake, Home, LogOut, Notebook, ReceiptIndianRupee } from "lucide-react";
import { RxDashboard } from "react-icons/rx";
import { FaBalanceScale } from 'react-icons/fa';
import { Settings } from 'lucide-react';
import { UserCircle } from 'lucide-react';
import { FaUserFriends } from 'react-icons/fa';
import { GoReport } from "react-icons/go";
import { SiLinphone } from "react-icons/si";
interface iMenu {
  id: string;
  title: string;
  url?: string;
  icon: any;
  submenus?: iMenu[];
  newUrl?: string;
}

// Define all menus
export const allMenus: iMenu[] = [

  {
    id: "dashboard_admin",
    title: "Dashboard",
    url: "/home/dashboard_admin",
    icon: RxDashboard,
  },

  {
    id: "dashboard_systemadmin",
    title: "Dashboard",
    url: "/home/dashboard_systemadmin",
    icon: RxDashboard,
  },

  {
    id: "dashboard_employee",
    title: "Dashboard",
    url: "/home/dashboard_employee",
    icon: RxDashboard,
  },

  {
    id: "dashboard_advocate",
    title: "Dashboard",
    url: "/home/dashboard_advocate",
    icon: RxDashboard,
  },

  {
    id: "dashboard_client",
    title: "Dashboard",
    url: "/home/dashboard_client",
    icon: RxDashboard,
  },


  { id: "company", title: "Companies", url: "/company", icon: Building2},
  { id: "invoicegenerate", title: "invoice", url: "/invoicegenerate", icon: Building2},
  { id: "newinvoice", title: "newinvoice", url: "/newinvoice", icon: Building2},

  {
    id: "contact",
    title: "Contact",
    url: "/contact",
    icon: FaUserFriends,
    submenus: [
      { id: "client", title: "Client", url: "/contact/client", icon: Handshake },
      { id: "parties", title: "Party", url: "/contact/party", icon: Home },
      { id: "advocate", title: "Advocate", url: "/contact/advocate", icon: Home },
      { id: "judge", title: "Judges", url: "/contact/judge", icon: Home },
      { id: "lawfirm", title: "Law Firms", url: "/contact/lawfirm", icon: Home },
      { id: "employee", title: "Employee", url: "/contact/employee", icon: Home },
      { id: "assigned_unassigned_clients", title: "Assigned / UnAssigned Clients", url: "/contact/assignedunassignedtoclient", icon: Handshake }
    ],
  },

  {
    id: "casemanagement",
    title: "Case",
    url: "/casemanagement",
    icon: FaBalanceScale,
    submenus: [
      { id: "case", title: "Cases", url: "/casemanagement/case", icon: Home },
      { id: "casesceduler", title: "Case Sceduler", url: "/calendar", icon: Home },
      { id: "casedates", title: "Case Dates", url: "/casemanagement/casedates", icon: Home },
      { id: "uploadfiles", title: "Upload Files", url: "/uploadfiles", icon: Home},
    ],
  },

  {
    id: "billspayments",
    title: "Bills & Payments",
    url: "/billspayments",
    icon: CreditCard,
    submenus: [
      { id: "invoice", title: "Invoice", url: "/billspayments/invoice", icon: Home},
      { id: "ledger", title: "Ledger", url: "/billspayments/ledger", icon: Home },
      { id: "receiptentry", title: "Receipt Entry", url: "/billspayments/receiptentry", icon: Home },
      { id: "receiptcancel", title: "Receipt Cancel", url: "/billspayments/receipt-cancel", icon: Home},
      { id: "invoicecancellation", title: "Invoice Cancel", url: "/billspayments/invoicecancellation", icon: Home}
    ]
  },

  {
    id: "reports",
    title: "Reports",
    url: "/reports",
    icon: GoReport,
    submenus: [
      { id: "casereport", title: "Case Reports", url: "/reports/casereport", icon: Home },
      { id: "casedatereport", title: "Case Date Reports", url: "/reports/casedatereport", icon: Home },
      { id: "caseorderreport", title: "Case Order Reports", url: "/reports/caseorderreport", icon: Home },
    ],
  },

  {
    id: "master",
    title: "Masters",
    url: "/master",
    icon: ReceiptIndianRupee,
    // submenus: [
    //   { id: "spare", title: "Spare", url: "/master/spare", icon: Home },
    //   { id: "vehicle", title: "Vehicle", url: "/master/vehicle", icon: Home },
    //    { id: "company", title: "company", url: "/master/company", icon: Home },
    //   { id: "courttype", title: "Court Type Master", url: "/master/courttype", icon: Home},
    //   { id: "supplier", title: "Supplier", url: "/master/supplier", icon: Home},
    //   { id: "category", title: "Category Master", url: "/master/category", icon: Home },
    //   { id: "courtmaster", title: "Court Master", url: "/master/courtmaster", icon: Home },
    //   { id: "casestatus", title: "Case Status", url: "/master/casestatus", icon: Home },
    //   { id: "stafftype", title: "Staff Type", url: "/master/stafftype", icon: Home },
    //   { id: "casestage", title: "Case Stages", url: "/master/casestage", icon: Home },
    //   { id: "ratetype", title: "Rate Type", url: "/master/ratetype", icon: Handshake },
    //   { id: "ratecontract", title: "Rate Contract", url: "/master/ratecontract", icon: Handshake },
    //   { id: "customer", title: "Customer", url: "/master/customer", icon: Handshake },
    //   { id: "destination", title: "Destination", url: "/master/destination", icon: Handshake },
    //   { id: "driver", title: "Driver", url: "/master/driver", icon: Handshake },
    //   // { id: "appearingfor", title: "Appearing For", url: "/master/appearingfor", icon: Home },
    // ],
  },

  {
    id: "userconfig",
    title: "User Config",
    url: "/userconfig/usermaster",
    icon: UserCircle,
    submenus: [
      { id: "usermaster", title: "User Master", url: "/userconfig/usermaster", icon: Home},
    ],
  },

  

  {
    id: "transactions",
    title: "Transactions",
    url: "/transactions",
    icon: SiLinphone,
  },


  {
    id: "myaccount",
    title: "My Account",
    url: "/myaccount",
    icon: Settings,
    submenus: [
      { id: "myprofile", title: "My Profile", url: "/myaccount/myprofile", icon: Home },
      { id: "companydetails", title: "Company Details", url: "/myaccount/companydetails", icon: Home },
    ],
  },
 
];

// Function to get menus based on role ID
export const getMenusForRole = (loggedInRoleId: string ) => {
  const allowedMenusByRole: Record<string, string[]> = {

      //Role-1 System Admin
     "1": ["dashboard_systemadmin", "company", "master","spare","vehicle","company","courttype","courtmaster","casestatus","casestage","ratecontract","ratetype","customer","destination","stafftype","supplier","category","userconfig","transactions", "driver"],

      // Role-id 2 Data Entry
     "2": ["dashboard_systemadmin", "company", "master","courttype","courtmaster","casestatus","casestage","stafftype","supplier","category","userconfig","transactions", "driver"],

      // Role-id 3 adminx
      "3": ["dashboard_admin","casemanagement","case","assigned_unassigned_clients","invoice","invoicecancellation", "receiptentry","receiptcancel","ledger","casesceduler","billspayments","bills","paymentsreceipts","reports","casereport", "casedatereport"
        ,"caseorderreport","causelistreportautomated","causelistposreportautomated","contact","client","parties","lawfirm","courtmaster","judge","advocate","employee","userconfig"],

      //Role-id 4 Staff/Employee
      "4": ["dashboard_employee","casemanagement","case", "casesceduler","billspayments","bills","invoice","invoicecancellation","receiptentry","receiptcancel","ledger","reports","casereport","casedatereport"
        ,"caseorderreport","causelistreportautomated","causelistposreportautomated"],

      // RoleId-5 Advocate
      "5": ["dashboard_advocate","casemanagement","case","billspayments","bills","invoice","receiptentry","receiptcancel","invoicecancellation","reports","casereport","casedatereport"
        ,"caseorderreport","causelistreportautomated","causelistposreportautomated"],

      //Role-Id 6 Client
      "6": ["dashboard_client","casemanagement","case", "uploadfiles","billspayments","receiptentry", "invoice", "ledger"],
      
      //Role-7 Party
      "7": ["home","casemanagement","case","casedates","casesceduler","billspayments","bills","paymentsreceipts","reports","casereport","casedatereport"
        ,"caseorderreport","causelistreportautomated","causelistposreportautomated"],
  };

  // Filter main menus
  const filteredMenus = allMenus
    .filter(menu => allowedMenusByRole[loggedInRoleId]?.includes(menu.id))
    .map(menu => {
      if (menu.submenus) {
        // Filter submenus if they exist
        const filteredSubmenus = menu.submenus.filter(submenu =>
          allowedMenusByRole[loggedInRoleId]?.includes(submenu.id)
        );
        return { ...menu, submenus: filteredSubmenus.length > 0 ? filteredSubmenus : undefined };
      }
      return menu;
    });

  return filteredMenus;
};

