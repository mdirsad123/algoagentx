'use client'
import FormHeader from '@/components/shared/form-header'
import { Building2 } from 'lucide-react'
import React from 'react'

import { ThreeDots } from 'react-loader-spinner';
import { useFetcher } from '@/hooks/use-query';
import ProductTable from '../components/product-table';


type Props = {}

function Page({}: Props) {

  const {data,isLoading}=useFetcher(`/product/product-list`,"product-list")
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center">
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
   <>
 
    <ProductTable productlist={data} />

</>

  )
}

export default Page