'use client'
import FormHeader from '@/components/shared/form-header'
import { Building2 } from 'lucide-react'
import React from 'react'

import { ThreeDots } from 'react-loader-spinner';
import { useFetcher } from '@/hooks/use-query';
import RateContract from '../components/ratecontract-form';
import RateContractTable from '../components/ratecontract-table';

type Props = {}

function Page({}: Props) {

  const {data,isLoading}=useFetcher(`/ratecontract/ratecontract-list`,"ratecontract-list-full")
  
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
 
    <RateContractTable ratecontractlist={data} />

</>

  )
}

export default Page