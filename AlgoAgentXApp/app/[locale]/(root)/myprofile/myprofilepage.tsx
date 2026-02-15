"use client";

import { Mail, MapPin, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { User } from "@/types/user-type";
import React, { useEffect, useRef, useState } from "react";
import { useRouter } from 'next/navigation';
import Toast from "@/components/shared/toast";
import { useFetcher, usePoster, useUpdater ,useUpdaterWithFileUpload} from "@/hooks/use-query";
import Cookies from "js-cookie";
import { getImageUrl } from "@/lib/utils";
import UserForm from "../userconfig/usermaster/components/user-form";
import { useTranslation } from "@/hooks/use-translations";

type Props = { UserProfile: User, onRefresh: () => void };

const MyProfile = ({ UserProfile, onRefresh }: Props) => {
  const router = useRouter();
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [userData, setUserData] = useState<User>(UserProfile);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const { t, isRTL} = useTranslation();

  // Popup state for edit
  const [isEditPopupOpen, setIsEditPopupOpen] = useState(false);

  // Update userData when UserProfile changes (after refetch)
  useEffect(() => {
    console.log("UserProfile updated:", UserProfile);
    setUserData(UserProfile);
    setImageUrl(UserProfile?.profile_image_url);
  }, [UserProfile]);

  const handleButtonClick = () => {
      fileInputRef.current?.click();
    };

    // Function to notify header component about image update
  const notifyImageUpdate = () => {
    // Dispatch custom event
    window.dispatchEvent(new CustomEvent('profileImageUpdated'));
    
    // Also set localStorage flag (as backup)
    localStorage.setItem('profileImageUpdated', Date.now().toString());
    
    console.log("Profile image update event dispatched");
  };

   const onSuccess = (response:User) => {
    console.log("Image upload success:", response);
    setImageUrl(response.profile_image_url);
    setUserData(response);
    
    // Trigger parent refetch
    if (typeof onRefresh === "function") {
      onRefresh();
    }
    
      // Notify header component about the update
    setTimeout(() => {
      notifyImageUpdate();
    }, 100); // Small delay to ensure state is updated

    
    Toast.fire({
      icon: "success",
      title: t("profile.Imageuploadsuccess"),
    });
  };
  
  const onError = (error:any) => {
    Toast.fire({
      icon: "error",
      title: error.response.data.message,
    });
  };

  const addUser = useUpdaterWithFileUpload (
      `/userconfig/update-profile-image/`,
      "userImageChange",
      onSuccess,
      onError
       
    );

 const MAX_FILE_SIZE = 1 * 1024 * 1024; // 5 MB

const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0];
  if (!file) {
    console.error("No file selected");
    return;
  }

  // File size validation
  if (file.size > MAX_FILE_SIZE) {
    Toast.fire({
      icon: "error",
      title: t("profile.filesizeerror"),
    });
    event.target.value = ""; // Reset the input
    return;
  }

  // Create a URL for preview
  const url = URL.createObjectURL(file);
  setImageUrl(url);

  // Prepare FormData
  const formData = new FormData();                                                                       
  formData.append("userid", String(loggedinuserid));
  formData.append("profile_image_url", file);

  // Log for debugging
  const entries = Array.from(formData.entries());
  entries.forEach(([key, value]) => {
    console.log(key, value);
  });

  console.log("Calling API with URL:", "/userconfig/update-profile-image");

  try {
    console.log("Uploading image for user id", loggedinuserid);
    addUser.mutate(formData);
  } catch (error) {
    console.error("Error uploading image:", error);
    Toast.fire({
      icon: "error",
      title: t("profile.ImageUploadFailed"),
    });
  }
};

  
  // Updated handleEditProfile to open popup
  const handleEditProfile = () => {
    console.log('Opening edit for User ID:', userData?.user_id);
    console.log('Current userData:', userData);
    setIsEditPopupOpen(true);
  };

  // Handle popup close
  const handleEditPopupClose = () => {
    setIsEditPopupOpen(false);
  };

  // Handle successful update from popup
  const handleEditSuccess = () => {
    console.log("Edit success callback triggered");
    
    // Close the popup first
    setIsEditPopupOpen(false);
    
    // Refresh the profile data
    if (typeof onRefresh === "function") {
      console.log("Calling onRefresh to update profile data");
      onRefresh();
    }
    
    // Notify header about the update
    setTimeout(() => {
      notifyImageUpdate();
    }, 100);
  };

  const handleDelete = () => {
    console.log("Delete profile image");
  };

  // Display the current userData (which should update when UserProfile changes)
  const displayData = userData || UserProfile;

  return (
  <>
    <form dir={isRTL ? "rtl" : "ltr"}>
      <div className="p-10 bg-gray-100 dark:bg-gray-900 h-full w-full">
        <div className="max-w-5xl mx-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          {/* Main Content */}
          <div className="p-6 bg-white dark:bg-gray-800">
            {/* Top Section - Profile Image and Buttons */}
            <div className="flex flex-col sm:flex-row items-center gap-4 mb-6">
              {/* Profile Image */}
              <div className="w-24 h-24 sm:w-28 sm:h-28 flex-shrink-0">
                {imageUrl ? (
                  <img
                    src={getImageUrl(imageUrl)}
                    alt="Profile"
                    className="w-full h-full rounded-full object-cover"
                    onError={() => setImageUrl("")}
                  />
                ) : (
                  <div className="w-full h-full rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                    <span className="text-gray-600 dark:text-gray-300 text-base font-medium">{t("profile.Profile")}</span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
                <input
                  type="file"
                  accept="image/*"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                />
                <Button
                  type="button"
                  // variant="outline"
                  className="w-full sm:w-[180px] h-[44px] px-4 text-sm bg-primary text-primary-foreground rounded-md"
                  onClick={handleButtonClick}
                >
                  {t("profile.UploadNewPicture")}
                </Button>
              </div>
            </div>

            {/* Bottom Section - Information Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Column */}
              <div className="space-y-4">
                {/* Name */}
                <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
                    {t("profile.Name")}
                  </label>
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 break-words">
                    {displayData?.fullname || "N/A"}
                  </h2>
                </div>

                {/* Phone */}
                <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
                    {t("profile.Phone")}
                  </label>
                  <span className="text-base text-gray-900 dark:text-gray-100">
                    {displayData?.mobile || "N/A"}
                  </span>
                </div>

                {/* Email */}
                <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
                    {t("profile.Email")}
                  </label>
                  <span className="text-base text-gray-900 dark:text-gray-100 break-words">
                    {displayData?.email || "N/A"}
                  </span>
                </div>
              </div>

              {/* Right Column */}
              <div className="flex flex-col justify-between">
                {/* Address */}
                <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg h-44">
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
                    {t("profile.Address")}
                  </label>
                  <div className="text-gray-900 dark:text-gray-100 leading-relaxed text-sm break-words">
                    {displayData?.address || "No address provided"}
                    <br />
                    {displayData?.city && displayData?.state
                      ? `${displayData.city}, ${displayData.state} ${displayData.pincode}`
                      : "N/A"}
                  </div>
                </div>

                {/* Buttons */}
                <div className="flex flex-col sm:flex-row justify-between items-center mt-6 gap-3">
                  <Button
                    type="button"
                    className="w-full sm:w-auto bg-primary text-primary-foreground px-6 py-2.5 text-sm font-medium rounded-md transition-colors"
                    onClick={handleEditProfile}
                  >
                   {t("profile.EditProfile")}
                  </Button>

                  <div className="bg-orange-500 text-white text-sm font-medium rounded-full px-4 py-1 text-center">
                    {displayData && (displayData.usertype_id === 1 ? displayData.userstatus : displayData.status) || t("profile.Active")}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </form>

    {/* Edit User Popup */}
    <UserForm
      user={userData}
      mode="edit"
      open={isEditPopupOpen}
      onOpenChange={handleEditPopupClose}
      onSuccess={handleEditSuccess}
      isProfileEdit={true}
    />
  </>
);
};

export default MyProfile;