"use client"

import { ColumnDef } from "@tanstack/react-table"
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export type Invoice = {
  id: string;
  invoiceNoDate: string;
  invoicefor: string;
  customer: string;
  company: string;
  from: string;
  dispatchno: string;
  product: string;
  packagedetails: string;
  invoiceamount: number;
}

export const columns: ColumnDef<Invoice>[] = [
  {
    accessorKey: "invoiceNoDate",
    header: "Invoice No./Date",
  },
  {
    accessorKey: "invoicefor",
    header: "Invoice For",
  },
  {
    accessorKey: "customer",
    header: "Customer",
  },
  {
    accessorKey: "company",
    header: "Company",
  },
  {
    accessorKey: "from",
    header: "From",
  },
  {
    accessorKey: "dispatchno",
    header: "Dispatch No.",
  },
  {
    accessorKey: "product",
    header: "Product",
  },
   {
    accessorKey: "packagedetails",
    header: "Package Details",
  },
  {
    accessorKey: "invoiceamount",
    header: "Invoice Amount",
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const hireSlip = row.original

      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuItem
              onClick={() => {}}
            >
              Copy hire slip ID
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => {}}
            >
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem className="text-red-600">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    },
  },
]