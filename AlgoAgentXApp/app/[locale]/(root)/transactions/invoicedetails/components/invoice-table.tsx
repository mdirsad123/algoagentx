"use client"

import * as React from "react"
import {
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"

import { ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { columns, Invoice } from "../columns"

// SAMPLE DATA
export const data: Invoice[] = [
  {
    id: "1",
    invoiceNoDate: "INV/2025/0012 / 28-10-2025",
    invoicefor: "Sun Agro Foods Pvt. Ltd.",
    customer: "Sun Agro Foods Pvt. Ltd.",
    company: "Horizon Logistics Pvt. Ltd.",
    from: "Bengaluru, Karnataka",
    dispatchno: "DSP/2025/0456",
    product: "Refined Sunflower Oil",
    packagedetails: "25 Tons",
    invoiceamount: 2500.00
  },
  {
    id: "2",
    invoiceNoDate: "INV/2025/0013 / 28-10-2025",
    invoicefor: "Sun Agro Foods Pvt. Ltd.",
    customer: "Sun Agro Foods Pvt. Ltd.",
    company: "Horizon Logistics Pvt. Ltd.",
    from: "Bengaluru, Karnataka",
    dispatchno: "DSP/2025/0457",
    product: "Refined Sunflower Oil",
    packagedetails: "25 Tons",
    invoiceamount: 2800.00
  }

]

export function InvoiceDetailsTable() {
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = React.useState({})

  const table = useReactTable({
    data,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  })

  const [showFilters, setShowFilters] = React.useState(true);

  return (
    <div className="w-full">

    <div className="flex justify-between items-center mb-3">
    <h2 className="text-lg font-semibold">Filters</h2>

    <button
        onClick={() => setShowFilters(!showFilters)}
        className="flex items-center gap-2 text-sm font-medium text-gray-700 border px-3 py-2 rounded-lg hover:bg-gray-100 transition"
    >
        {showFilters ? "Hide Filters" : "Show Filters"}
        <ChevronDown
        className={`h-4 w-4 transition-transform duration-300 ${
            showFilters ? "rotate-180" : "rotate-0"
        }`}
        />
    </button>
    </div>

    {/* --------------------- FILTER PANEL --------------------- */}
    <div
        className={`w-full bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden transition-all duration-300 ${
        showFilters ? "p-5 max-h-[800px] opacity-100" : "p-0 max-h-0 opacity-0"
        }`}
    >
    {/* Row 1 */}
    <div className="grid grid-cols-4 gap-4 mb-4">
        <Input placeholder="Invoice For" className="h-11 rounded-lg" />
        <Input placeholder="Invoice No." className="h-11 rounded-lg" />

        <div className="relative">
        <Input placeholder="Invoice Dates" className="h-11 rounded-lg pr-10" />
        <span className="absolute right-3 top-3 text-gray-500">📅</span>
        </div>

        <Input placeholder="Customer" className="h-11 rounded-lg" />
    </div>

    {/* Row 2 */}
    <div className="grid grid-cols-4 gap-4 mb-4">
        <Input placeholder="Company" className="h-11 rounded-lg" />

        <div className="relative">
        <Input placeholder="From Location" className="h-11 rounded-lg pr-10" />
        <span className="absolute right-3 top-3 text-gray-500">➤</span>
        </div>

        <div className="relative">
        <Input placeholder="To Location" className="h-11 rounded-lg pr-10" />
        <span className="absolute right-3 top-3 text-gray-500">➤</span>
        </div>

        <Input placeholder="Products" className="h-11 rounded-lg" />
    </div>

    {/* Row 3 */}
    <div className="grid grid-cols-4 gap-4 mb-4">
        <Input placeholder="Vehicle No." className="h-11 rounded-lg" />
        <Input placeholder="Status" className="h-11 rounded-lg" />
        <Input placeholder="Acknowledgment No." className="h-11 rounded-lg" />

        <div className="relative">
        <Input placeholder="Acknowledgment Dates" className="h-11 rounded-lg pr-10" />
        <span className="absolute right-3 top-3 text-gray-500">📅</span>
        </div>
    </div>

    {/* Row 4 */}
    <div className="grid grid-cols-4 gap-4 mb-4">
        <Input placeholder="Dispatch No." className="h-11 rounded-lg" />

        <div className="relative">
        <Input placeholder="Dispatch Dates" className="h-11 rounded-lg pr-10" />
        <span className="absolute right-3 top-3 text-gray-500">📅</span>
        </div>

        <Input placeholder="Hire Slip No." className="h-11 rounded-lg" />

        <div className="relative">
        <Input placeholder="Hire Slip Dates" className="h-11 rounded-lg pr-10" />
        <span className="absolute right-3 top-3 text-gray-500">📅</span>
        </div>
    </div>

    {/* Row 5 */}
    <div className="grid grid-cols-4 gap-4 mb-4">
        <Input placeholder="Booking No." className="h-11 rounded-lg" />

        <div className="relative">
        <Input placeholder="Booking Dates" className="h-11 rounded-lg pr-10" />
        <span className="absolute right-3 top-3 text-gray-500">📅</span>
        </div>

        <div></div>

        {/* Search Button Right Aligned */}
        <div className="flex justify-end">
        <Button className="h-11 px-10 rounded-lg text-base flex items-center gap-2">
            🔍 Search
        </Button>
        </div>
    </div>

    </div>


      {/* SPACING */}
      <div className="mt-6"></div>

      {/* ------------------- TOP RIGHT TOOLBAR (PDF/EXCEL/COLUMNS) ------------------- */}
      <div className="flex items-center justify-between py-4 bg-white rounded-lg">
        <Input
          placeholder="Search"
          value={(table.getColumn("customer")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("customer")?.setFilterValue(event.target.value)
          }
          className="w-[260px] h-10 rounded-lg border-gray-300 shadow-sm"
        />

        <div className="flex gap-3">
          <Button
            variant="outline"
            className="h-10 px-4 rounded-lg border-gray-300 shadow-sm"
          >
            PDF
          </Button>

          <Button
            variant="outline"
            className="h-10 px-4 rounded-lg border-gray-300 shadow-sm"
          >
            Excel
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="h-10 px-4 rounded-lg border-gray-300 shadow-sm"
              >
                Columns <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {table
                .getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => (
                  <DropdownMenuCheckboxItem
                    key={column.id}
                    className="capitalize"
                    checked={column.getIsVisible()}
                    onCheckedChange={(value) => column.toggleVisibility(!!value)}
                  >
                    {column.id}
                  </DropdownMenuCheckboxItem>
                ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* ------------------------ TABLE ------------------------ */}
      <div className="rounded-md border mt-2 bg-white shadow-sm">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="text-gray-700">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>

          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} className="hover:bg-gray-50 text-sm">
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="py-3">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-center py-10 text-gray-500"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* ------------------------ PAGINATION ------------------------ */}
      <div className="flex items-center justify-end space-x-2 py-4">
        <div className="flex-1 text-sm text-gray-600">
          {table.getFilteredSelectedRowModel().rows.length} of{" "}
          {table.getFilteredRowModel().rows.length} row(s) selected.
        </div>

        <div className="space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="rounded-lg"
          >
            Previous
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="rounded-lg"
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
