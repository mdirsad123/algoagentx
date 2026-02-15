
import { Company } from "@/types/company-type";
import { User } from "@/types/user-type";
import { atom } from "jotai";
import { atomWithStorage } from "jotai/utils"
import { secureStorage } from "./secure-atom";
export const atomSelectedCompany=atomWithStorage<Partial<Company>>("selectedCompany",{});
export const atomShowPanel=atom<boolean>(false);
export const atomCompany=atom<Company>();
export const atomClient=atom<any>({});
export const atomCurrentUser = atomWithStorage<Partial<User>>("currentUser", {}, secureStorage);
export const atomShowCasePopup=atom<boolean>(false);
export const atomShowClientPopup=atom<boolean>(false);
export const atomProfileImageUrl = atom<string | null>(null);
export const atomShowPartyPopup=atom<boolean>(false);
export const atomShowAdvocatePopup=atom<boolean>(false);
export const atomShowCourtPopup=atom<boolean>(false);
export const atomShowCouncilPopup=atom<boolean>(false);
export const atomNotifications = atom<any[]>([]);
export const atomShowLawfirmPopup=atom<boolean>(false);
export const atomShowAppearingforPopup=atom<boolean>(false);
export const atomShowJudgePopup=atom<boolean>(false);