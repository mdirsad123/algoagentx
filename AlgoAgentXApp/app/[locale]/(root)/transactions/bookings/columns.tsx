"use client";

import { ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal, Pencil, Trash2, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Booking } from "@/types/booking.type";

export const BookingColumn = ({
  onView = () => {},
  onEdit = () => {},
}: {
  onView?: (data: Booking) => void;
  onEdit?: (data: Booking) => void;
}): ColumnDef<Booking>[] => {
  return [
    {
      accessorKey: "booking_no",
      header: "Booking No",
    },
    {
      accessorKey: "customer_name",
      header: "Customer",
    },
    {
      accessorKey: "from_destination",
      header: "From Destination",
    },
    {
      accessorKey: "to_destination",
      header: "To Destination",
    },
    {
      accessorKey: "vehicle_no",
      header: "Vehicle",
    },
    {
      accessorKey: "booking_date",
      header: "Booking Date",
      cell: ({ row }) =>
        new Date(row.original.booking_date).toLocaleDateString(),
    },
    {
      accessorKey: "status",
      header: "Status",
    },

    // ✅ ACTIONS COLUMN
    {
      accessorKey: "booking_id", // ✅ EXISTING FIELD
      id: "actions",
      header: "Actions",
      meta: { export: false },
      cell: ({ row }) => {
        const booking = row.original;

        const btn =
          "h-9 w-9 flex items-center justify-center rounded-lg bg-white border border-gray-200 shadow-sm hover:bg-gray-100 cursor-pointer";

        return (
          <div className="flex gap-2">
            <div className={btn} onClick={() => onView(booking)}>
              <Eye size={16} className="text-gray-700" />
            </div>

            <div className={btn} onClick={() => onEdit(booking)}>
              <Pencil size={16} className="text-gray-700" />
            </div>
          </div>
        );
      },
    },
  ];
};
