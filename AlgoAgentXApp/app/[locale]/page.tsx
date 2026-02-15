import { redirect } from "next/navigation";
export default async function Lawyer() {
  redirect("/auth/login");
};
