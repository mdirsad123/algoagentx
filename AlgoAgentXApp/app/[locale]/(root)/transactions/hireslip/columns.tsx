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

export type HireSlip = {
  id: string;
  hireSlipNoDate: string;
  bookingNoDate: string;
  customer: string;
  company: string;
  from: string;
  to: string;
  vehicleTrip: string;
  supplier: string;
  product: string;
  trips: number;
}

export const columns: ColumnDef<HireSlip>[] = [
  {
    accessorKey: "hireSlipNoDate",
    header: "Hire Slip No./Date",
  },
  {
    accessorKey: "bookingNoDate",
    header: "Booking No./Date",
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
    accessorKey: "to",
    header: "To",
  },
  {
    accessorKey: "vehicleTrip",
    header: "Vehicle / Trip Details",
  },
  {
    accessorKey: "supplier",
    header: "Supplier",
  },
  {
    accessorKey: "product",
    header: "Product",
  },
  {
    accessorKey: "trips",
    header: "P",
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
              onClick={() => navigator.clipboard.writeText(hireSlip.id)}
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