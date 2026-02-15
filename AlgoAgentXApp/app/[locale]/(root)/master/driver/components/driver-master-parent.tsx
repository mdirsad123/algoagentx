"use client";
import React, { useState, useEffect } from "react";
import DriverBasicForm from "./driver-basic";
import DriverNomineeForm from "./driver-nominee";
import DriverInfoForm from "./driver-info";
import DriverDocsForm from "./driver-docs";
import DriverBankForm from "./driver-bank";

const tabs = [
  { id: 1, label: "Driver Basic Info" },
  { id: 2, label: "Driver Nominee" },
  { id: 3, label: "Driver Documents" },
  { id: 4, label: "Driver Info" },
  { id: 5, label: "Driver Bank" },
];

const DriverMasterParent = ({
  id,
  mode,
  personal,
  documents,
  nominees,
  bank,
  info,
  refetch, // ✅ ADD THIS PROP to refetch data after update
}: any) => {
  console.log("🔥 DriverMasterParent Mounted");
  console.log("Received Personal:", personal);
  console.log("Received Documents:", documents);
  console.log("Received Nominees:", nominees);
  console.log("Received Bank:", bank);
  console.log("Received Info:", info);

  const [currentStep, setCurrentStep] = useState(1);

  // Load on client-side only
  // useEffect(() => {
  //   if (typeof window !== "undefined") {
  //     // ✅ ALWAYS start from tab 1 in edit mode
  //     if (mode === "edit") {
  //       setCurrentStep(1);
  //       localStorage.setItem("current_step", "1");
  //     } else {
  //       // Only load saved step in add mode
  //       const saved = localStorage.getItem("current_step");
  //       if (saved) setCurrentStep(Number(saved));
  //     }
  //   }
  // }, [mode]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      // ✅ ALWAYS start from tab 1 for both add and edit mode
      setCurrentStep(1);
      localStorage.setItem("current_step", "1");
    }
  }, []); // ✅ Empty dependency array = runs only once on mount

  // Cleanup: Clear localStorage when component unmounts (user leaves page)
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined") {
        localStorage.removeItem("current_step");
      }
    };
  }, []);

  const [allFormData, setAllFormData] = useState({});

  // ⭐ LOAD FORM DATA IN EDIT MODE
  useEffect(() => {
    if (mode === "edit" && personal) {
      setAllFormData({
        ...personal,
        documents: documents || [],
        nominees: nominees || [],
        bank: bank || [],
        info: info || {}, // ✅ This should contain driver_info_id
      });
    }
  }, [mode, personal, documents, nominees, bank, info]);

  useEffect(() => {
    console.log("🔥 From Parent — nominees received:", nominees);
  }, [nominees]);

  const updateData = (data: any) => {
    setAllFormData((prev) => ({ ...prev, ...data }));
  };

  const goToNextStep = () => {
    setCurrentStep((prev) => {
      const next = prev + 1;
      localStorage.setItem("current_step", String(next));
      return next;
    });
  };

  const handleTabClick = (step: number) => {
    setCurrentStep(step);
    localStorage.setItem("current_step", String(step));
  };

  const driverId = id && id !== "null" ? Number(id) : null;

  return (
    <>
      {/* ---------- TABS UI ---------- */}
      <div className="w-full flex border-b border-gray-300 dark:border-gray-700 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabClick(tab.id)}
            className={`px-6 py-3 text-sm font-medium 
              ${
                currentStep === tab.id
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-600 dark:text-gray-300 hover:text-blue-500"
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ---------- FORM SECTIONS ---------- */}
      <div className="mt-6">
        {currentStep === 1 && (
          <DriverBasicForm
            mode={driverId ? "edit" : "add"}
            id={driverId ?? undefined}
            initialData={allFormData}
            onNext={goToNextStep}
          />
        )}

        {currentStep === 2 && (
          <DriverNomineeForm
            mode={mode}
            initialData={allFormData}
            onNext={goToNextStep}
            onChange={updateData}
          />
        )}

        {currentStep === 3 && (
          <DriverDocsForm
            driverId={driverId}
            driverdocs={documents?.[0]}
            initialData={documents?.[0] || {}}
            onNext={goToNextStep}
          />
        )}

        {currentStep === 4 && (
          <DriverInfoForm
            driverId={driverId}
            mode={mode}
            driverinfo={info} // ✅ PASS THE INFO OBJECT (contains driver_info_id)
            initialData={info || {}}
            onNext={goToNextStep}
            onChange={updateData}
          />
        )}

        {currentStep === 5 && (
          <DriverBankForm
          driverId={driverId}
            mode={mode}
            driverbank={bank?.[0]} // ✅ ADD THIS to pass bank data with IDs
            initialData={bank?.[0] || {}}
            onNext={goToNextStep}
          />
        )}
      </div>
    </>
  );
};

export default DriverMasterParent;
