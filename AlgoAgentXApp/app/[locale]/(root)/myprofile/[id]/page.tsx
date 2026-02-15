"use client";
import { useFetcher } from "@/hooks/use-query";
import MyProfile from "../myprofilepage";
import { useParams } from "next/navigation";
import { useTranslation } from "@/hooks/use-translations";

type Props = {};

const Page = (props: Props) => {
  const param = useParams();

  const { data: userdataforprofile, refetch, isLoading } = useFetcher(
    `/userconfig/userprofile/${param.id}`,
    "profilebyid"
  );

  console.log("got profile data", userdataforprofile);

  // Enhanced refetch function with logging
  const handleRefresh = async () => {
    console.log("Profile refetch triggered");
    try {
      await refetch();
      console.log("Profile refetch completed");
    } catch (error) {
      console.error("Profile refetch failed:", error);
    }
  };

  const{t} = useTranslation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p>{t("profile.LoadingProfile")} </p>
        </div>
      </div>
    );
  }

  return userdataforprofile ? (
    <MyProfile UserProfile={userdataforprofile} onRefresh={handleRefresh} />
  ) : (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center text-red-600">
        <p>{t("profile.FailedToLoadProfile")} </p>
        <button 
          onClick={handleRefresh}
          className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {t("profile.Retry")}
        </button>
      </div>
    </div>
  );
};

export default Page;