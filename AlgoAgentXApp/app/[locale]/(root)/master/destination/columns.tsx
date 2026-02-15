"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ColumnDef } from "@tanstack/react-table";
import { Eye, MoreHorizontal, Pencil, Trash } from "lucide-react";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";
import { useRouter } from "next/navigation";
import { Destination } from "@/types/destination-type";

export const DestinationColumns = ({
  onView = () => {},
  onEdit = () => {},
  onDelete = () => {},
}: {
  onView?: (data: Destination) => void;
  onEdit?: (data: Destination) => void;
  onDelete?: (data: Destination) => void;
}): ColumnDef<Destination>[] => [
  {
    accessorKey: "dest_code",
    meta: "Destination Code",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Destination Code" />
    ),
  },

  {
    accessorKey: "destination",
    meta: "Destination",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Destination" />
    ),
  },

  {
    accessorKey: "country",
    meta: "Country",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Country" />
    ),
  },

  {
    accessorKey: "state",
    meta: "State",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="State" />
    ),
  },

  {
    accessorKey: "city",
    meta: "City",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="City" />
    ),
  },

  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => {
        const item = row.original;

        return (
        <div className="flex items-center gap-2">
            {/* View */}
            <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700"
                onClick={() => onView(item)}
            >
            <Eye className="h-4 w-4 text-gray-700 dark:text-gray-300" />
            </Button>

            {/* Edit */}
            <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700"
                onClick={() => onEdit(item)}
            >
            <Pencil className="h-4 w-4 text-gray-700 dark:text-gray-300" />
            </Button>

            {/* Delete */}
            <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700"
                onClick={() => onDelete(item)}
            >
            <Trash className="h-4 w-4 text-red-600" />
            </Button>
        </div>
        );
    },
},

];
