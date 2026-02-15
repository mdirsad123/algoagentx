'use client'
import React, { useState, useEffect } from 'react'
import CategoryForm from "../components/orders-form";
import { ThreeDots } from 'react-loader-spinner';
import { useFetcher } from '@/hooks/use-query';
import { Button } from '@/components/ui/button';
import { FileText, FileSpreadsheet, Plus, Search } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { useTranslation } from "@/hooks/use-translations"; // ← Import the hook
import OrderForm from '../components/orders-form';
import OrderproductForm from '../components/orders-form';
import { OrderTable } from '../components/orders-table';

type Props = {}

function Page({}: Props) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'add' | 'edit' | 'view'>('add');
  const [searchTerm, setSearchTerm] = useState("");
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const { data, isLoading, refetch } = useFetcher(`/order/orderlist`, "orderListdsv");


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

      <div className="p-5 bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100 transition-colors duration-300">
       <OrderTable  />
     </div>
  )
}

export default Page