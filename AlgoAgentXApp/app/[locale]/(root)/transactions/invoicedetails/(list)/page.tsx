'use client'
import React, { useState, useEffect } from 'react'
import Supplierform from "../components/invoice-form";
import { ThreeDots } from 'react-loader-spinner';
import { useFetcher } from '@/hooks/use-query';
import { Button } from '@/components/ui/button';
import { FileText, FileSpreadsheet, Plus, Search } from 'lucide-react';
import { Input } from "@/components/ui/input";
import HireSlipForm from '../components/invoice-form';

type Props = {}

function Page({}: Props) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'add' | 'edit' | 'view'>('add');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const { data, isLoading, refetch } = useFetcher(`/master/appearingfor`, "appearingfor");

  // useEffect to refetch data when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger > 0) {
      refetch();
    }
  }, [refreshTrigger, refetch]);

  

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-gray-50">
        <section className="p-5">
          <ThreeDots
            height="80"
            width="80"
            color="#4fa94d"
            ariaLabel="tail-spin-loading"
            wrapperStyle={{}}
            wrapperClass=""
            visible={true}
          />
        </section>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white  px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            
            
          </div>
        </div>
      </div>

      {/* Appearing For Table */}


      {/* Modal Form */}
      <HireSlipForm
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        mode={modalMode}
        asDialog={true}
       
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  )
}

export default Page