// "use client";
// import { ChevronLeft, Truck, PlusSquare, LucideIcon } from "lucide-react";
// import { useI18n, defineLocale } from "@/locales/client";
// import dynamicIconImports from "lucide-react/dynamicIconImports";
// import Link from "next/link";
// import React, { useEffect, useState } from "react";
// import { Button } from "@/components/ui/button";
// import { getMenusForRole } from "@/data";
// import {
//   Accordion,
//   AccordionContent,
//   AccordionItem,
//   AccordionTrigger,
// } from "@/components/ui/accordion";
// // import Icon from "./customicon";
// import { usePathname } from "next/navigation";
// import { cn } from "@/lib/utils";
// import { useWindowWidth } from "@react-hook/window-size";
// import Cookies from "js-cookie";

// import {
//   TooltipProvider,
//   Tooltip,
//   TooltipContent,
//   TooltipTrigger,
// } from "@/components/ui/tooltip";

// export default function SideBar() {
//   const onlyWidth = useWindowWidth();
//   const mobileWidth = onlyWidth < 768;

//   interface MenuTitleProps {
//     title: JSX.Element | string;
//     // iconname: keyof typeof dynamicIconImports;
//     Icon: LucideIcon;
//     url?: string;
//     newRrl?: string;
//   }
//   const t = useI18n();

//   const [LoggedInUserRoleId] = useState(Cookies.get("loggedinuserroleid"));
//   const [menuValue, setMenuValue] = useState("");
//   const [isCollapsed, setIsCollapsed] = useState(false);
//   const toggleSidebar = () => {
//     if (!isCollapsed) setMenuValue("");
//     setIsCollapsed(!isCollapsed);
//     console.log(isCollapsed);
//   };

//   const MenuTitle = ({ title, Icon }: MenuTitleProps) => {
//     return (
//       <>
//         <Icon className="w-4 h-4" />

//         {!isCollapsed ? <span className="capitalize">{title}</span> : <></>}
//       </>
//     );
//   };
//   const SubMenuItem = ({ title, url = "#", newRrl = "#" }: MenuTitleProps) => {
//     const isActive=pathname===url || pathname.startsWith(url);
//     return (
//       <div className={cn("flex group w-full items-center justify-between space-x-2 pl-9 pr-4 py-1 my-0.5 rounded-md hover:bg-highlight hover:text-highlight-foreground ",{"bg-highlight text-highlight-foreground":isActive})}>
//         <Link href={url} className="w-full">
//           <span className="capitalize">{title}</span>
//         </Link>
//         {newRrl != "#" ? (
//           <Link href={newRrl}>
//             <PlusSquare className=" invisible w-4 h-4 group-hover:visible" />
//           </Link>
//         ) : (
//           <></>
//         )}
//       </div>
//     );
//   };
//   const MainMenu = ({ title, Icon, url = "#" }: MenuTitleProps) => {
//     const isActive=pathname===url || pathname.startsWith(url);
//     return (
//       <Link
//         href={url}
//         className={cn("flex w-full items-center justify-start gap-2 px-3 py-1 my-0.5 rounded-md hover:bg-highlight hover:text-highlight-foreground ",{"bg-highlight text-highlight-foreground":isActive})}
//       >
//         <Icon className="w-4 h-4" />
//         {!isCollapsed ? <span className="capitalize">{title}</span> : <></>}
//       </Link>
//     );
//   };
//   const pathname = usePathname();
//   useEffect(() => {
//     setIsCollapsed(mobileWidth ? true : false);
//     console.log(mobileWidth);
//     return () => {};
//   }, [mobileWidth]);


//   return (
//     <div
//       className={cn(
//         "flex relative z-50 shrink-0 max-sm:hidden sm:w-[60px] min-h-screen bg-primary text-primary-foreground dark:bg-card dark:text-card-foreground transition-all ease-linear duration-300",
//         `${isCollapsed ? "w-[60px]" : "md:w-[230px]"}`
//       )}
//     >
//       <div
//         className={cn(
//           "fixed transition-all ease-linear duration-300",
//           `${isCollapsed ? "w-[60px]" : "md:w-[230px]"}`
//         )}
//       >
//         <div className="flex flex-col ">
//           <Link
//             href="#"
//             className="flex  w-full items-center justify-center text-highlight space-x-2  bg-primary brightness-75 p-3 top-0 dark:bg-card dark:text-card-foreground "
//           >
//             <Truck />
//             {!isCollapsed ? (
//               <span className="shrink-0 font-bold uppercase">
//                 {t("common.appTitle")}
//               </span>
//             ) : (
//               <></>
//             )}
//           </Link>
//           <nav className="flex  flex-col gap-2 p-2 h-screen scrollbar-thin scrollbar-thumb-primary scrollbar-track-transparent  hover:overflow-y-auto">
//             <Accordion
//               type="single"
//               value={menuValue}
//               collapsible
//               onValueChange={(e) => {
//                 setMenuValue(e);
//               }}
//             >
//               {LoggedInUserRoleId && getMenusForRole(LoggedInUserRoleId).map((item, i) => {
//                 if (item.submenus) {
//                   const isActive=pathname===item.url || pathname.startsWith(item.url!);
//                   return (
//                     <Tooltip key={i}>
//                       <TooltipTrigger asChild>
//                         <AccordionItem value={item.title}>
//                           <AccordionTrigger
//                             data-showicon={!isCollapsed}
//                             onClick={() => setIsCollapsed(false)}
//                             className={cn("flex w-full items-center justify-start gap-2 px-3 py-1 my-0.5 hover:bg-highlight hover:text-highlight-foreground rounded-md",{"text-highlight ":isActive})}
//                           >
//                             <MenuTitle
//                               title={t(
//                                 `menus.${item.id}` as keyof typeof defineLocale
//                               )}
//                               Icon={
//                                 item.icon
//                                 // item.icon as keyof typeof dynamicIconImports
//                               }
//                             />
//                           </AccordionTrigger>
//                           <AccordionContent>
//                             {item.submenus.map((subitem, j) => {
//                               return (
//                                 <SubMenuItem
//                                   key={j}
//                                   // title={subitem.title}
//                                   title={t(
//                                     `menus.${subitem.id}` as keyof typeof defineLocale
//                                   )}
//                                   url={subitem.url}
//                                   Icon={subitem.icon}
//                                   newRrl={subitem.newUrl}
//                                 />
//                               );
//                             })}
//                           </AccordionContent>
//                         </AccordionItem>
//                       </TooltipTrigger>
//                       <TooltipContent side="right" hidden={!isCollapsed}>
//                         <span>{item.title}</span>
//                       </TooltipContent>
//                     </Tooltip>
//                   );
//                 } else {
//                   return (
//                     <Tooltip key={i}>
//                       <TooltipTrigger asChild>
//                         <AccordionItem value={item.title} >
//                           <MainMenu
//                             title={t(
//                               `menus.${item.id}` as keyof typeof defineLocale
//                             )}
//                             Icon={item.icon}
//                             url={item.url}
//                           />
//                         </AccordionItem>
//                       </TooltipTrigger>
//                       <TooltipContent side="right" hidden={!isCollapsed} >
//                         <span>{item.title}</span>
//                       </TooltipContent>
//                     </Tooltip>
//                   );
//                 }
//               })}
//             </Accordion>
//           </nav>
//         </div>
//         <div className="flex flex-col sticky  max-md:hidden bottom-0">
//           <Button
//             onClick={toggleSidebar}
//             className="bg-primary brightness-75 dark:bg-card  hover:brightness-50 rounded-none items-center justify-center p-3"
//           >
//             <ChevronLeft
//               className={cn(
//                 "text-primary-foreground dark:text-card-foreground",
//                 `${isCollapsed ? "rotate-180" : "rotate-0"}`
//               )}
//             />
//           </Button>
//         </div>
//       </div>
//     </div>
//   );
// }
