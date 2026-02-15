'use client';

import React, { useState } from "react";
import Cookies from "js-cookie";
import { X } from "lucide-react";
import { useRouter } from "next/navigation"; 
import { useUpdater } from "@/hooks/use-query";
import { NotificationType } from "@/types/notification-type";
import { FaFileInvoiceDollar } from "react-icons/fa";
import { SiInvoiceninja } from "react-icons/si";
import { PiInvoice } from "react-icons/pi";
import { formatDistanceToNowStrict } from 'date-fns';
import { FcBriefcase } from "react-icons/fc";
import { 
  FaBell, 
  FaUser, 
  FaFileAlt, 
  FaCalendar, 
  FaDollarSign,
  FaExclamationTriangle 
} from 'react-icons/fa';
import { 
  IoBriefcase, 
  IoDocument, 
  IoPersonAdd,
  IoCalendarOutline,
  IoNotifications 
} from 'react-icons/io5';
import { FaBook } from "react-icons/fa";
import { MdMessage } from "react-icons/md";

const iconMap: { [key: string]: React.ElementType } = {
  FaFileInvoiceDollar,
  PiInvoice,
  SiInvoiceninja,
  IoBriefcase,
  IoDocument,
  FcBriefcase,
  IoPersonAdd,
  IoCalendarOutline,
  IoNotifications,
  FaBell,
  FaUser,
  FaFileAlt,
  FaCalendar,
  FaDollarSign,
  FaExclamationTriangle,
  FaBook,
};

type MessageProps = {
  data: NotificationType;
  i: number;
  user_uuid: string;
  notifications: NotificationType[];
  onClose: () => void;
  onSeeAll?: () => void;
};

const Message = ({
  data,
  i,
  user_uuid,
  notifications,
  onClose,
  onSeeAll,
}: MessageProps) => {
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const [expandedIds, setExpandedIds] = useState<string[]>([]);
  const router = useRouter();

  const MAX_LENGTH = 100;

  const toggleExpand = (id: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent notification click when expanding
    setExpandedIds((prev) =>
      prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]
    );
  };

    const handleSeeAll = () => {
    onClose(); // close drawer first
    setTimeout(() => {
      router.push("/notifications");
    }, 100);
  };

  // 🔑 Open "See All" page when clicking a single notification
  const handleNotificationClick = () => {
    handleSeeAll();
  };

  return (
    <div className="h-full w-full bg-white dark:bg-gray-900 rounded-l-2xl shadow-md border-l border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col transition-colors duration-300">
   {/* Header */}
   <div className="sticky top-0 z-10 bg-white dark:bg-gray-900 flex items-center justify-between px-3 sm:px-6 py-3 sm:py-4 border-b border-gray-200 dark:border-gray-700">
     <h2 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100">Notifications</h2>
        <button
          onClick={onClose}
          className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700 px-2 sm:px-3">
        {notifications.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-10">
            No notifications.
          </div>
        ) : (
          notifications.slice(0, 10).map((notification) => {
            const IconComponent = iconMap[notification.icon ?? ""];
            const isExpanded = expandedIds.includes(notification.id.toString());
            const message =
              notification.message.length > MAX_LENGTH && !isExpanded
                ? notification.message.slice(0, MAX_LENGTH) + "..."
                : notification.message;

            return (
              <div
                key={notification.id}
                className="flex gap-3 sm:gap-4 px-3 sm:px-4 py-4 sm:py-5 hover:bg-gray-50 dark:hover:bg-gray-800 transition relative cursor-pointer"
                onClick={handleNotificationClick}
              >
                {/* Icon */}
                <div className="w-8 h-8 sm:w-10 sm:h-10 flex-shrink-0 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                  <MdMessage className="text-lg sm:text-xl text-blue-500" />
                </div>

                {/* Message */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-1 break-words">
                    {notification.title}
                  </p>
                  <div className="text-sm text-gray-600 dark:text-gray-400 break-words">
                    <div dangerouslySetInnerHTML={{ __html: message }} />
                    {notification.message.length > MAX_LENGTH && (
                      <button
                        onClick={(e) => toggleExpand(notification.id.toString(), e)}
                        className="ml-1 text-blue-500 dark:text-blue-400 text-xs underline"
                      >
                        {isExpanded ? "Show less" : "Read more"}
                      </button>
                    )}
                  </div>
                </div>

                {/* Time */}
                <div className="absolute bottom-2 right-3 sm:right-4 text-[10px] sm:text-[11px] text-gray-400 dark:text-gray-500 whitespace-nowrap">
                  {formatDistanceToNowStrict(new Date(notification.createdAt), { addSuffix: true })}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* See All Button */}
      {notifications.length > 10 && (
        <div className="border-t border-gray-200 dark:border-gray-700 px-3 sm:px-4 py-2 sm:py-3 bg-white dark:bg-gray-900">
          <button
            onClick={handleSeeAll}
            className="w-full py-2 px-3 sm:px-4 bg-blue-600 dark:bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors duration-200"
          >
            See All ({notifications.length})
          </button>
        </div>
      )}
    </div>
  );
};

export default Message;