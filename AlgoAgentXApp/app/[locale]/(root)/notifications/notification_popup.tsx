import { useEffect, useRef, useState } from "react";
import Cookies from "js-cookie";
import { useFetcher } from "@/hooks/use-query";
import { NotificationType } from "@/types/notification-type";
import Message from "./components/message";

interface PopupProps {
  isOpen: boolean;
  onClose: () => void;
}

const Popup: React.FC<PopupProps> = ({ isOpen, onClose }) => {
  const popupRef = useRef<HTMLDivElement>(null);
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const [shouldRender, setShouldRender] = useState(isOpen);

  const { data: notifications, refetch: fetchNotifications } = useFetcher(
    `/notifications/my/${loggedinuserid}`,
    "notifications",
    !!loggedinuserid
  );

  useEffect(() => {
    if (loggedinuserid) {
      fetchNotifications();
    }
  }, [loggedinuserid]);

  // Delay unmount to allow slide-out animation
  useEffect(() => {
    if (isOpen) {
      setShouldRender(true);
    } else {
      const timeout = setTimeout(() => setShouldRender(false), 300); // match duration
      return () => clearTimeout(timeout);
    }
  }, [isOpen]);

  // Close when clicked outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        popupRef.current &&
        !popupRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!shouldRender || !notifications) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className={`fixed inset-0 bg-black bg-opacity-30 dark:bg-opacity-50 z-40 transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        ref={popupRef}
        className={`fixed top-0 right-0 h-full w-full sm:w-[400px] bg-white dark:bg-gray-800 z-50 shadow-lg rounded-l-2xl
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        <Message
          data={notifications[0]}
          i={0}
          user_uuid={loggedinuserid!}
          notifications={notifications}
          onClose={onClose}
        />
      </div>
    </>
  );
};

export default Popup;
