import { FileSpreadsheet } from "lucide-react";
import { z } from "zod";

export const RoleSchema = z.object({
    code: z.string().optional(),
    rolename: z.string().min(1, { message: "Role Name is mandatory" }),
    isAdmin: z.boolean().default(false) ,
});