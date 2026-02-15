"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { InvoicePaymentReceiptType } from "@/types/invoicepaymentreceipt-type";

export const ReceiptColumns = ({
  onEdit = () => {},
  onView = () => {},
  onCancel = () => {},
  onHistory = () => {},
  onChequeStatus = () => {}
}: {
  onEdit?: (data: InvoicePaymentReceiptType) => void;
  onView?: (data: InvoicePaymentReceiptType) => void;
  onCancel?: (data: InvoicePaymentReceiptType) => void;
  onHistory?: (data: InvoicePaymentReceiptType) => void;
  onChequeStatus?: (data: InvoicePaymentReceiptType) => void;
}): ColumnDef<InvoicePaymentReceiptType>[] => [

  // -------------------------------------------------------
  // RECEIPT DETAIL
  // -------------------------------------------------------
  {
    accessorKey: "receipt_no",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Receipt Detail" />
    ),
    cell: ({ row }) => (
      <div className="text-sm">
        <b>{row.original.receipt_no}</b>

        <div className="text-xs text-gray-500">
          on {row.original.created_on}
        </div>

        <div className="text-xs text-gray-500">
          by {row.original.created_by}
        </div>
      </div>
    ),
  },

  // CUSTOMER
  {
    accessorKey: "customer",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Customer" />
    ),
  },

  // COMPANY
  {
    accessorKey: "company",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Company" />
    ),
  },

  // PRODUCT
  {
    accessorKey: "product",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Product" />
    ),
  },

  // RECEIVED AGAINST
  {
    accessorKey: "received_against",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Received Against" />
    ),
    cell: ({ row }) => (
      <div>{row.original.received_against}</div>
    ),
  },

  // RECEIVED AMOUNT
  {
    accessorKey: "received_amt",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Received Amt" />
    ),
    cell: ({ row }) => (
      <div className="font-medium text-blue-600">
        ₹ {Number(row.original.received_amt).toLocaleString()}
      </div>
    ),
  },

  // CHEQUE DETAILS
  {
    accessorKey: "cheque_detail",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Cheque Detail" />
    ),
    cell: ({ row }) => (
      <div className="text-sm">
        Chq No.: <b>{row.original.cheque_no}</b><br />
        Chq Dt.: {row.original.cheque_date}<br />
        Bank: {row.original.bank_name}
      </div>
    ),
  },

  // MODIFIED BY / ON
  {
    accessorKey: "modified_by",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Modified By / On" />
    ),
    cell: ({ row }) => (
      <div className="text-sm">
        <b>{row.original.modified_by}</b><br />
        <span className="text-xs text-gray-500">{row.original.modified_on}</span>
      </div>
    ),
  },

  // STATUS WITH COLORS
  {
    accessorKey: "status",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Status" />
    ),
    cell: ({ row }) => {
      const status = row.original.status;

      const colors: any = {
        Received: "bg-green-500 text-white",
        Deposited: "bg-yellow-400 text-black",
        Cleared: "bg-blue-500 text-white",
      };

      return (
        <div
          className={`px-3 py-1 rounded text-xs font-bold text-center w-28 ${colors[status]}`}
        >
          {status}
        </div>
      );
    },
  },

  // ACTION MENU
  {
    id: "actions",
    header: "Action",
    cell: ({ row }) => {
      const data = row.original;

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
              Cancel
            </DropdownMenuItem>

            <DropdownMenuItem onClick={() => onChequeStatus(data)}>
              Cheque Status Update
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );
    },
  },

];
