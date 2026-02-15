"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";

export function SupplierStatusDialog({ open, onClose, supplier, onSubmit }: any) {
  const [selected, setSelected] = useState("Inactive");

  useEffect(() => {
    if (supplier) {
      setSelected(supplier.status === "Active" ? "Active" : "Inactive");
    }
  }, [supplier]);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="space-y-4">
        <DialogHeader>
          <DialogTitle>Change Supplier Status</DialogTitle>
        </DialogHeader>

        <div className="text-sm font-semibold text-gray-700">
          supplier:{" "}
          <span className="font-bold text-black">
            {supplier?.supplier_name}
          </span>
        </div>

        <div className="flex gap-6 mt-2">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="status"
              value="Active"
              checked={selected === "Active"}
              onChange={() => setSelected("Active")}
            />
            Active
          </label>

          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="status"
              value="Inactive"
              checked={selected === "Inactive"}
              onChange={() => setSelected("Inactive")}
            />
            Inactive
          </label>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <Button
            onClick={() => onSubmit(selected)}
            className="px-6 py-2 bg-gray-800 text-white rounded-md"
          >
            Save Status
          </Button>

          <Button
            onClick={onClose}
            className="px-6 py-2 bg-red-800 text-white rounded-md"
          >
            Cancel
          </Button>          
        </div>
      </DialogContent>
    </Dialog>
  );
}
