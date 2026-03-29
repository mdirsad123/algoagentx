"use client";
import moment from "moment";
import { CalendarIcon, X } from "lucide-react";
import { format } from "date-fns";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar, CalendarProps } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

import React, { ComponentProps, forwardRef, useState } from "react";
import { PopoverClose } from "@radix-ui/react-popover";
import { DayPicker, SelectSingleEventHandler } from "react-day-picker";

type DatePickerProps = ComponentProps<typeof DayPicker> & {
  className?: string;
  selected:any, 
  onSelect:any,
  placeholder?: string;
  format?:string;
};

const DatePicker = ({
  className,
  
  
  selected, 
  onSelect,
  placeholder,
  format="DD-MMM-yyyy",
  ...props
}: DatePickerProps) => {
  
  const [isPopoverOpen, setIsPopoverOpen] = React.useState(false)

  const handleOnSelect: SelectSingleEventHandler = (date) => {
    onSelect?.(date)
    setIsPopoverOpen(false)
  }
  return (
    <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
      <PopoverTrigger asChild>
        <Button
          variant={"outline"}
          className={cn("flex w-full h-9 px-3 text-left font-normal", className)}
        >
          {selected ? (
            moment(selected).format(format)
          ) : (
            <span>{placeholder}</span>
          )}
          <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        {/* <PopoverClose> */}
          <Calendar {...props} selected={selected} mode="single" onSelect={handleOnSelect}   />
        {/* </PopoverClose> */}
      </PopoverContent>
    </Popover>
  );
};
export default DatePicker;
