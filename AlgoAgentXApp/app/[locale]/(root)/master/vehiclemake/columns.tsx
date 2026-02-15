"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Eye, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Vehiclemake } from "@/types/vehiclemake-type";


  export const CategoryColumns = ({
     onDelete = () => {},
     onView = () => {},
     onEdit = () => {},
       }: {
     onDelete?: (data: Vehiclemake) => void;
     onView?: (data: Vehiclemake) => void;
     onEdit?: (data:Vehiclemake) => void;
  }): ColumnDef<Vehiclemake>[] => [
  {
    accessorKey: "vehicle_code",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Vehicle code" />
    ),
},

  {
    accessorKey: "vehicle_name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Vehicle Name" />
    ),
  },
  
  {
    accessorKey: "description",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Description" />
    ),
  },
  
 
  {
    id: "actions",
    header: "Action",
    cell: ({ row }) => {
      const data = row.original;
      
       return (
        <div className="flex items-center space-x-2">
          <TooltipProvider>

            {/* View */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                className="p-2 rounded bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-300 dark:hover:bg-green-800"
                onClick={() => onView(data)}>
                  <Eye size={14}/>
                </Button>
              </TooltipTrigger>
              <TooltipContent>View</TooltipContent>
            </Tooltip>

            {/* Edit */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                className="p-2 rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200 dark:bg-yellow-900 dark:text-yellow-300 dark:hover:bg-yellow-800"
                onClick={() => onEdit(data)}>
                  <Pencil size={14} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Edit</TooltipContent>
            </Tooltip>

            {/* Delete */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                className="p-2 rounded bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-300 dark:hover:bg-red-800"
                onClick={() => onDelete(data)}>
                  <Trash2 size={14} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Delete</TooltipContent>
            </Tooltip>

          </TooltipProvider>
        </div>
      );
    },
  },

];
