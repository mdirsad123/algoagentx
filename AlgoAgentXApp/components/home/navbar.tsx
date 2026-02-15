"use client";
import {
  Bell,
  Building,
  Home,
  LayoutGrid,
  ListTodo,
  MessageSquare,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState } from "react";
import { useI18n } from "@/locales/client";
import { atomSelectedCompany } from "@/stores";
import { useAtom } from "jotai";
import Cookies from "js-cookie";

export default function HomeNavbar() {
  const [selectedCompany] = useAtom(atomSelectedCompany);
  const [loggedinuserfullname] = useState(Cookies.get("loggedinuserfullname"));
  const pathname = usePathname();
  const t = useI18n();
  const links = [
    {
      id: "dashboard",
      title: "Dashboard",
      url: "/home/dashboard",
      icon: LayoutGrid,
    },
    { id: "tasks", title: "Pending Tasks", url: "/home/tasks", icon: ListTodo },
  ];
  return (
    <div className="h-32 p-5 border-b  sticky -top-7 z-40 bg-secondary w-full shrink-0">
      <div className="flex space-x-3 ">
        <div className="flex w-12 h-12 rounded-lg border bg-primary items-center justify-center">
          <Home className="text-muted" />
        </div>
        <div className="flex flex-col">
          <p>
            {/* {t("dashboard.hello")},{" "} */}
            <span className="font-semibold">{loggedinuserfullname}</span>
          </p>
          <span className="text-sm">{selectedCompany.company_name}</span>
        </div>
      </div>
      <nav className="mt-5  flex space-x-4 text-sm font-medium text-center text-secondary-foreground">
        {links.map((item, i) => {
          return (
            <Link
              key={i}
              href={item.url}
              className={`${
                pathname === item.url
                  ? "inline-flex items-center justify-center py-2.5 text-primary border-b-2 border-primary group"
                  : "inline-flex items-center justify-center py-2.5 border-b-2 border-transparent  rounded-t-lg text-opacity-80 hover:text-opacity-100 hover:border-muted-foreground/30 group"
              }`}
            >
              <item.icon
                className={`${
                  pathname === item.url
                    ? "w-4 h-4 me-2 text-primary"
                    : "w-4 h-4 me-2 text-gray-400 group-hover:text-gray-500 dark:text-gray-500 dark:group-hover:text-gray-300"
                }`}
              />
              {/* {t(`dashboard.${item.id}` as keyof typeof defineLocale)} */}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
