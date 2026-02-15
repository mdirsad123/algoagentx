"use client";
import { ColumnDef } from "@tanstack/react-table";
import { Eye, Pencil, Trash2 } from "lucide-react";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";
import { useState } from "react";
import Cookies from "js-cookie";
import { Tooltip } from "@radix-ui/react-tooltip";
import { TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Order } from "@/types/order-type";

export const orderColumns = ({
  onView = () => {},
  onEdit = () => {},
  onDelete = () => {},
}: {
  onView?: (data: Order) => void;
  onEdit?: (data: Order) => void;
  onDelete?: (data: Order) => void;
}): ColumnDef<Order>[] => {
  return [
    {
      id: "order_info",
      meta: "Order Details",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Order Details" />
      ),
      accessorFn: (row) =>
        `${row.order_no || ""}\n${
          row.order_date
            ? new Date(row.order_date).toLocaleDateString("en-GB")
            : ""
        }`,
      size: 220,
      cell: ({ row }) => {
        const Order = row.original;
        return (
          <div className="flex flex-col p-3 space-y-1 font-poppins dark:text-gray-200">
            <span className="text-base font-semibold">
              {Order.order_no || "N/A"}
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {Order.order_date
                ? new Date(Order.order_date).toLocaleDateString("en-GB")
                : "N/A"}
            </span>
          </div>
        );
      },
    },

    {
      id: "consumer_info",
      meta: "Consumers",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Consumers" />
      ),
      accessorFn: (row) =>
        `${row.company_name || ""} ${row.customer_name || ""}`,
      size: 220,
      cell: ({ row }) => {
        const data = row.original;

        const companyName = data.company_name || "N/A";
        const customerName = data.customer_name || "N/A";

        return (
          <div className="flex flex-col p-3 space-y-1 font-poppins dark:text-gray-200">
            <span className="text-sm whitespace-nowrap">
              <span className="font-semibold">Company:</span> {companyName}
            </span>

            <span className="text-sm whitespace-nowrap">
              <span className="font-semibold">Customer:</span> {customerName}
            </span>
          </div>
        );
      },
    },

    {
      id: "destination_from",
      meta: "Destination From",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Destination From" />
      ),
      accessorKey: "destination_from",
      size: 180,
      cell: ({ row }) => {
        const val = row.original.destination_from_name;
        return (
          <span className="p-3 font-poppins text-sm dark:text-gray-200">
            {val || "N/A"}
          </span>
        );
      },
    },

    {
      id: "destination_to",
      meta: "Destination To",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Destination To" />
      ),
      accessorKey: "destination_to",
      size: 180,
      cell: ({ row }) => {
        const val = row.original.destination_to_name;
        return (
          <span className="p-3 font-poppins text-sm dark:text-gray-200">
            {val || "N/A"}
          </span>
        );
      },
    },

    {
      id: "dispatch_info",
      meta: "Dispatch Details",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Dispatch Details" />
      ),
      accessorFn: (row) => {
        const from = row.dispatch_from
          ? new Date(row.dispatch_from).toLocaleDateString("en-GB")
          : "";
        const to = row.dispatch_to
          ? new Date(row.dispatch_to).toLocaleDateString("en-GB")
          : "";
        return `${from} ${to}`;
      },
      size: 200,
      cell: ({ row }) => {
        const data = row.original;

        const dispatchFrom = data.dispatch_from
          ? new Date(data.dispatch_from).toLocaleDateString("en-GB")
          : "N/A";

        const dispatchTo = data.dispatch_to
          ? new Date(data.dispatch_to).toLocaleDateString("en-GB")
          : "N/A";

        return (
          <div className="flex flex-col p-3 space-y-1 font-poppins dark:text-gray-200">
            <span className="text-sm whitespace-nowrap">
              <span className="font-semibold">Dispatch From:</span>{" "}
              {dispatchFrom}
            </span>

            <span className="text-sm whitespace-nowrap">
              <span className="font-semibold">Dispatch To:</span> {dispatchTo}
            </span>
          </div>
        );
      },
    },

    {
      id: "status_updatedon",
      meta: "Status | Updated By | On",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Status | Updated | On" />
      ),
      accessorFn: (row) =>
        `${row.status || ""}\n\nUpdated By: ${
          row.status_updatedby || ""
        }\nOn: ${
          row.modified_on
            ? new Date(row.modified_on).toLocaleString("en-GB")
            : ""
        }`,
      size: 240,
      cell: ({ row }) => {
        const Order = row.original;

        const formatDate = (dateString: string | Date | null | undefined) => {
          if (!dateString) return "-";
          return new Date(dateString).toLocaleString("en-GB", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          });
        };

        // Map status to colors
        const statusColors: Record<string, string> = {
          Pending: "bg-yellow-100 text-yellow-800",
          Approved: "bg-green-100 text-green-800",
          Rejected: "bg-red-100 text-red-800",
          InProgress: "bg-blue-100 text-blue-800",
          Completed: "bg-purple-100 text-purple-800",
        };

        const statusClass = Order.status
          ? statusColors[Order.status] || "bg-gray-100 text-gray-800"
          : "bg-gray-100 text-gray-800";

        return (
          <div className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors">
            <div className="space-y-2">
              <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <div className="font-medium">
                  <span
                    className={`px-2 py-1 rounded text-xs font-semibold ${statusClass}`}
                  >
                    {Order.status || "-"}
                  </span>
                </div>
                <div className="font-medium">
                  By:{" "}
                  <span className="font-normal">
                    {Order.created_by_name || "-"}
                  </span>
                </div>
                <div className="font-medium">
                  On:{" "}
                  <span className="font-normal">
                    {formatDate(Order.modified_on)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      },
    },

    {
      id: "actions",
      meta: { export: false },
      header: ({ column }) => (
        <DataTableColumnHeader
          column={column}
          title="Actions"
          className="text-slate-700 dark:text-gray-200 font-medium text-sm"
        />
      ),
      size: 140,
      cell: ({ row }) => {
        const Order = row.original;

        return (
          <div className="py-4 px-2 flex flex-col gap-2">
            <div className="flex items-center gap-2">
              {/* View button (always visible) */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onView(Order)}
                    className="p-2 rounded bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-200 hover:bg-green-200 dark:hover:bg-green-700 flex items-center justify-center"
                    title="View"
                  >
                    <Eye size={16} />
                  </button>
                </TooltipTrigger>
                <TooltipContent>View Order</TooltipContent>
              </Tooltip>

              {/* Edit button (conditional) */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onEdit(Order)}
                    className="p-2 rounded bg-yellow-100 dark:bg-yellow-800 text-yellow-700 dark:text-yellow-200 hover:bg-yellow-200 dark:hover:bg-yellow-700 flex items-center justify-center"
                    title="Edit Order"
                  >
                    <Pencil size={16} />
                  </button>
                </TooltipTrigger>
                <TooltipContent>Edit Order</TooltipContent>
              </Tooltip>
            </div>
          </div>
        );
      },
    },
  ];
};
