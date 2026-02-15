"use client";

import React, { useState, useEffect } from "react";
import { ThreeDots } from "react-loader-spinner";
import { useDeleter, useUpdater } from "@/hooks/use-query";
import { Company } from "@/types/company-type";
import { DataTable } from "@/components/shared/data-table";
import { CompanyColumns } from "../columns";
import { useRouter } from "next/navigation";
import Toast from "@/components/shared/toast";
import Swal from "sweetalert2";
import { CompanyStatusDialog } from "./companystatuspopup";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";

type Props = { companyList: Company[] };

const FleetCompanyTable = ({ companyList }: Props) => {
  const router = useRouter();

  const [statusDialog, setStatusDialog] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [spinning, setSpinning] = useState(false);

  const [filters, setFilters] = useState({
    company_name: "",
    city: "",
  });

  const [filteredCompanies, setFilteredCompanies] =
    useState<Company[]>(companyList);

  useEffect(() => {
    setSpinning(true);
    setTimeout(() => setSpinning(false), 600);
    setFilteredCompanies(companyList);
  }, [companyList]);

  const applyFilter = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_SERVER}/company/filterlist`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(filters),
        }
      );

      const result = await res.json();
      setFilteredCompanies(result);
    } catch (error) {
      console.error("Filter Error:", error);
    }
  };

  const handleRowView = (row: Company) => {
    router.push(`/master/company/${row.company_id}`);
  };

  const handleRowEdit = (row: Company) => {
    router.push(`/master/company/edit/${row.company_id}`);
  };

  const onSuccess = (response: Company) => {
    Toast.fire({
      icon: "success",
      title: "Company deleted!",
    });
  };

  const onError = (error: any) => {
    console.error("Delete error:", error);
    Toast.fire({
      icon: "error",
      title: "Submission Failed",
      text: error?.response?.data?.message || error.message,
    });
  };

  const deleteCompany = useDeleter(
    "company/delete/",
    "companyList",
    onSuccess,
    onError
  );

  const handleDelete = async (row: Company) => {
    const result = await Swal.fire({
      title: "Are you sure you want to delete this company?",
      text: row.company_name,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Yes, delete",
      cancelButtonText: "Cancel",
    });

    if (result.isConfirmed) {
      deleteCompany.mutate(row.company_id);
    }
  };

  const openStatusDialog = (company: Company) => {
    setSelectedCompany(company);
    setStatusDialog(true);
  };

  // API CALL to update status
  const updateStatus = useUpdater(
    "/company/update-status",
    "companyList",
    () => {
      Toast.fire({ icon: "success", title: "Status Updated!" });
      setStatusDialog(false);
    },
    (error: any) => {
      Toast.fire({
        icon: "error",
        text: error?.response?.data?.message || error.message,
      });
    }
  );

  // Save from popup
  const handleSubmitStatus = (newStatus: "Active" | "Inactive") => {
    updateStatus.mutate({
      company_id: selectedCompany?.company_id,
      status: newStatus,
    });
  };

  return (
    <div className="w-full p-4">
      <div className="w-full bg-white p-4 rounded-lg shadow-sm border flex flex-wrap items-end gap-4">
        <div className="flex flex-col w-56">
          <label className="text-sm font-medium text-gray-700 mb-1">
            Company Name
          </label>
          <input
            className="border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none p-2 rounded-md text-sm"
            placeholder="Search company name"
            value={filters.company_name}
            onChange={(e) =>
              setFilters({ ...filters, company_name: e.target.value })
            }
          />
        </div>

        <div className="flex flex-col w-56">
          <label className="text-sm font-medium text-gray-700 mb-1">City</label>
          <input
            className="border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none p-2 rounded-md text-sm"
            placeholder="Search City"
            value={filters.city}
            onChange={(e) => setFilters({ ...filters, city: e.target.value })}
          />
        </div>

        <div className="flex items-center gap-2 mt-1">
          <Button
            onClick={applyFilter}
            className="bg-orange-600 hover:bg-orange-700 text-white h-10 px-5"
          >
            Search
          </Button>

          <Button
            className="h-10 px-5"
            variant="outline"
            onClick={() => {
              setFilters({ company_name: "", city: "" });
              setFilteredCompanies(companyList);
            }}
          >
            <RotateCcw
              size={16}
              className={
                spinning ? "animate-spin [animation-direction:reverse]" : ""
              }
            />
          </Button>
        </div>
      </div>

      <DataTable
        columns={CompanyColumns({
          onEdit: handleRowEdit,
          onView: handleRowView,
          onDelete: handleDelete,
          onStatusToggle: openStatusDialog,
        })}
        data={filteredCompanies}
        showSearch={false}
        showPagination={true}
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          csv: true,
          pdf: true,
          filename: "company",
          title: "Company List",
        }}
      />

      {/* STATUS POPUP */}
      {selectedCompany && (
        <CompanyStatusDialog
          open={statusDialog}
          onClose={() => setStatusDialog(false)}
          company={selectedCompany}
          onSubmit={handleSubmitStatus}
        />
      )}
    </div>
  );
};

export default FleetCompanyTable;
