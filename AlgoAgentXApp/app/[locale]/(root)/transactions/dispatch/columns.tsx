"use client";

import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ColumnDef } from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";
import { DispatchType } from "@/types/dispatch-type";
// import { useRouter } from "next/navigation";

export const DispatchColumns = ({
  onDelete = () => {},
  onCancel = () => {},
  onView = () => {},
  onEdit = () => {},
  onHistory = () => {}
}: {
  onDelete?: (data: DispatchType) => void;
  onCancel?: (data: DispatchType) => void;
  onView?: (data: DispatchType) => void;
  onHistory?: (data: DispatchType) => void;
  onEdit?: (data:DispatchType) => void;

}): ColumnDef<DispatchType>[] => [

  {
    accessorKey: "dispatch_no",
    meta: "Dispatch No./DT",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Dispatch No./DT" />
    ),
    cell: ({ row }) => (
      <div>
        <b>{row.original.dispatch_no}</b>
        <div>{row.original.dispatch_date}</div>

        <div className="text-xs text-gray-500 mt-1">
          <b>Created By:</b> {row.original.created_by}
        </div>
      </div>
    )
  },

  {
    accessorKey: "booking_no",
    meta: "Booking No./DT",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Booking No./DT" />
    ),
    cell: ({ row }) => (
      <div>
        <b>{row.original.booking_no}</b>
        <div>{row.original.booking_date}</div>

        <div className="text-xs text-gray-500 mt-1">
          <b>Booking Created By:</b> {row.original.booking_created_by}
        </div>
      </div>
    )
  },

  {
    accessorKey: "customer",
    meta: "Customer",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Customer" />
    )
  },

  {
    accessorKey: "company",
    meta: "Company",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Company" />
    )
  },

  {
    accessorKey: "from_location",
    meta: "From",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="From" />
    )
  },

  {
    accessorKey: "to_location",
    meta: "To",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="To" />
    )
  },

  {
    accessorKey: "vehicle_no",
    meta: "Vehicle / Trip Detail",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Vehicle / Trip Detail" />
    ),
    cell: ({ row }) => {
      const d = row.original;
      return (
        <div>
          <div><b>Vehicle No:</b> {d.vehicle_no}</div>
          <div><b>Driver 1:</b> {d.driver1}</div>
          <div><b>Driver 2:</b> {d.driver2}</div>

          <div className="pt-1 text-xs text-gray-500">
            <b>Trip No:</b> {d.trip_no}  
          </div>
          <div className="text-xs text-gray-500">
            {d.trip_start} → {d.trip_end}
          </div>
        </div>
      );
    }
  },

 
  {
    accessorKey: "supplier",
    meta: "Supplier",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Supplier" />
    )
  },

  {
    accessorKey: "product",
    meta: "Product",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Product" />
    )
  },

  
  {
    accessorKey: "dispatch_amount",
    meta: "Dispatched Amt",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Dispatched Amt" />
    ),
    cell: ({ row }) => (
      <div className="text-green-600 font-semibold">
        ₹ {row.original.dispatch_amount}
      </div>
    )
  },

 
  {
    accessorKey: "invoice_amount",
    meta: "Invoice Amt",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Invoice Amt" />
    ),
    cell: ({ row }) => (
      <div className="text-blue-600 font-semibold">
        ₹ {row.original.invoice_amount}
      </div>
    )
  },

  {
    accessorKey: "received_amount",
    meta: "Tot Received",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Tot Received" />
    ),
    cell: ({ row }) => (
      <div className="text-purple-600 font-semibold">
        ₹ {row.original.received_amount}
      </div>
    )
  },

  
  {
    accessorKey: "balance",
    meta: "Balance",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Balance" />
    ),
    cell: ({ row }) => (
      <div className="text-red-600 font-semibold">
        ₹ {row.original.balance}
      </div>
    )
  },

  {
    accessorKey: "modified_by",
    meta: "Modified By / Modified On",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Modified By / On" />
    ),
    cell: ({ row }) => (
      <div>
        <b>{row.original.modified_by}</b>
        <div className="text-xs text-gray-500">{row.original.modified_on}</div>
      </div>
    )
  },

  
  {
    accessorKey: "status",
    meta: "Status",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Status" />
    ),
    cell: ({ row }) => {
      const status = row.original.status;

      const colors: any = {
        Dispatched: "bg-green-500 text-white",
        Acknowledged: "bg-yellow-400 text-black",
        "Invoice Generated": "bg-blue-500 text-white",
        "Partial Paid": "bg-orange-500 text-white",
        Paid: "bg-green-700 text-white",
        Cancelled: "bg-red-600 text-white",
      };

      return (
        <div className={`px-2 py-1 rounded text-xs font-bold text-center w-32 ${colors[status]}`}>
          {status}
        </div>
      );
    }
  },

  {
     id: "actions",
     header: "Action",
     cell: ({ row }) => {
       const data = row.original;
      //  const router = useRouter();
 
       return (
         <DropdownMenu>
           <DropdownMenuTrigger asChild>
             <Button variant="ghost" className="h-4 w-4 p-0">
               <MoreHorizontal className="h-4 w-4" />
             </Button>
           </DropdownMenuTrigger>
 
           <DropdownMenuContent align="end">
             <DropdownMenuLabel>Actions</DropdownMenuLabel>
 
             <DropdownMenuItem onClick={() => onView(data)}>View</DropdownMenuItem>
 
             <DropdownMenuItem onClick={() => onEdit(data)}>Edit</DropdownMenuItem>
 
             <DropdownMenuItem onClick={() => onHistory(data)}>History</DropdownMenuItem>
 
             <DropdownMenuItem onClick={() => onCancel(data)} className="text-red-600">
               Cancel Dispatch
             </DropdownMenuItem>
 
             <DropdownMenuItem onClick={() => onDelete(data)} className="text-red-600">
               Delete
             </DropdownMenuItem>
 
           </DropdownMenuContent>
         </DropdownMenu>
       );
     }
   }

];
