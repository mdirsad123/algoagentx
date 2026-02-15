"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState, useEffect, useMemo } from "react";
import { ControllerRenderProps } from "react-hook-form";
import { X } from "lucide-react";
import Toast from "@/components/shared/toast";

// Order item structure (supports full Prisma order object)
export type OrderItem = {
  id: number;
  name: string;
  date: string;

  // Destination names (used in popup table)
  from?: string | null;
  to?: string | null;

  // Full raw order object (contains products & IDs & destinations)
  raw?: any;
};


type MultiSelectPopupProps = {
  open: boolean;
  onClose: (open: boolean) => void;
  items: OrderItem[];
  field: ControllerRenderProps<any, any>;
};

export function MultiSelectPopup({
  open,
  onClose,
  items,
  field,
}: MultiSelectPopupProps) {
  const [search, setSearch] = useState("");
  const [tempSelected, setTempSelected] = useState<OrderItem[]>([]);

  // Load current selection when popup opens
  useEffect(() => {
    if (open) {
      setTempSelected(field.value || []);
    }
  }, [open, field.value]);

  // Filter orders by search
  const filtered = useMemo(() => {
    return items.filter((item) => {
      const s = search.toLowerCase();
      return (
        item.name.toLowerCase().includes(s) ||
        item.date.toLowerCase().includes(s)
      );
    });
  }, [items, search]);

  // Save selection
  const handleOK = () => {
    if (tempSelected.length > 1) {
      const first = tempSelected[0];

      const hasMismatch = tempSelected.some(
        (o) => o.from !== first.from || o.to !== first.to
      );

      if (hasMismatch) {
        Toast.fire({
          icon: "warning",
          title:
            "All selected orders must have the same From and To destinations.",
        });
        return; // ❌ stop — do NOT close popup
      }
    }

    // ✅ Valid → Save & close popup
    field.onChange(tempSelected);
    setSearch("");
    onClose(false);
  };

  // Cancel (restore previous selection)
  const handleCancel = () => {
    setTempSelected(field.value || []);
    setSearch("");
    onClose(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleCancel}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex justify-between items-center">
            <DialogTitle>Select Orders</DialogTitle>

            <button
              onClick={handleCancel}
              className="rounded-sm opacity-70 hover:opacity-100"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </DialogHeader>

        {/* Search Box */}
        <Input
          placeholder="Search orders..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-10 mt-2"
        />

        {/* Table */}
        <div className="mt-4 max-h-80 overflow-y-auto border rounded">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 dark:bg-gray-800 sticky top-0 z-10">
              <tr>
                <th className="p-2 w-10 text-center">✔</th>
                <th className="p-2 text-left">Order No</th>
                <th className="p-2 text-left">Date</th>
                <th className="p-2 text-left">From Destination</th>
                <th className="p-2 text-left">To Destination</th>
              </tr>
            </thead>

            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-3 text-center text-gray-500">
                    No matching orders
                  </td>
                </tr>
              ) : (
                filtered.map((item) => {
                  const isChecked = tempSelected.some((v) => v.id === item.id);

                  return (
                    <tr
                      key={item.id}
                      className="border-t hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <td className="text-center p-2">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setTempSelected([...tempSelected, item]);
                            } else {
                              setTempSelected(
                                tempSelected.filter((v) => v.id !== item.id)
                              );
                            }
                          }}
                        />
                      </td>

                      <td className="p-2">{item.name}</td>
                      <td className="p-2">{item.date}</td>

                      {/* ⭐ NEW FIELDS */}
                      <td className="p-2">{item.from ?? "-"}</td>
                      <td className="p-2">{item.to ?? "-"}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Action Buttons */}
        <div className="mt-4 flex justify-end gap-3">
          <Button
            variant="outline"
            className="h-10 px-6"
            onClick={handleCancel}
          >
            Cancel
          </Button>

          <Button
            className="h-10 px-6 bg-gray-900 text-white"
            onClick={handleOK}
          >
            OK
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
