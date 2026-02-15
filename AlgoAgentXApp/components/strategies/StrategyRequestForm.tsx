import * as React from "react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { toast } from "@/components/ui/use-toast"
import { useRouter } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2, Send } from "lucide-react"
import axiosInstance from "@/lib/axios"

const strategyRequestSchema = z.object({
  title: z.string().min(2, "Title must be at least 2 characters"),
  strategy_type: z.string().optional(),
  market: z.string().optional(),
  timeframe: z.string().optional(),
  indicators: z.string().optional(),
  entry_rules: z.string().min(10, "Entry rules must be at least 10 characters"),
  exit_rules: z.string().min(10, "Exit rules must be at least 10 characters"),
  risk_rules: z.string().min(10, "Risk rules must be at least 10 characters"),
  notes: z.string().optional(),
})

type StrategyRequestFormData = z.infer<typeof strategyRequestSchema>

interface StrategyRequestFormProps {
  onSuccess?: () => void
}

export function StrategyRequestForm({ onSuccess }: StrategyRequestFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const router = useRouter()

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<StrategyRequestFormData>({
    resolver: zodResolver(strategyRequestSchema),
    defaultValues: {
      title: "",
      strategy_type: "",
      market: "",
      timeframe: "",
      indicators: "",
      entry_rules: "",
      exit_rules: "",
      risk_rules: "",
      notes: "",
    },
  })

  const onSubmit = async (data: StrategyRequestFormData) => {
    try {
      setIsSubmitting(true)

      // Parse indicators if provided
      let indicatorsObj = undefined
      if (data.indicators && data.indicators.trim()) {
        try {
          indicatorsObj = JSON.parse(data.indicators)
        } catch (e) {
          toast({
            variant: "destructive",
            title: "Invalid JSON",
            description: "Please provide valid JSON format for indicators.",
          })
          return
        }
      }

      const requestData = {
        ...data,
        indicators: indicatorsObj,
      }

      const response = await fetch("/api/v1/strategy-requests", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to submit strategy request")
      }

      const result = await response.json()
      
      toast({
        title: "Strategy Request Submitted",
        description: "Your strategy request has been successfully submitted. We'll review it and get back to you soon.",
      })

      reset()
      if (onSuccess) {
        onSuccess()
      }
    } catch (error) {
      console.error("Error submitting strategy request:", error)
      toast({
        variant: "destructive",
        title: "Submission Failed",
        description: error instanceof Error ? error.message : "An error occurred while submitting your request.",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Request Custom Strategy</CardTitle>
        <CardDescription>
          Fill out the form below to request a custom trading strategy. Our team will review your requirements and get back to you.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">
              Strategy Title <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              placeholder="e.g., EMA Crossover Strategy"
              {...register("title")}
            />
            {errors.title && (
              <p className="text-sm text-red-500">{errors.title.message}</p>
            )}
          </div>

          {/* Basic Information */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="strategy_type">Strategy Type</Label>
              <Select onValueChange={(value) => register("strategy_type").onChange({ target: { value } })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="trend">Trend Following</SelectItem>
                  <SelectItem value="mean_reversion">Mean Reversion</SelectItem>
                  <SelectItem value="breakout">Breakout</SelectItem>
                  <SelectItem value="scalping">Scalping</SelectItem>
                  <SelectItem value="swing">Swing Trading</SelectItem>
                  <SelectItem value="position">Position Trading</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="market">Market</Label>
              <Select onValueChange={(value) => register("market").onChange({ target: { value } })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select market" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="equity">Equity</SelectItem>
                  <SelectItem value="forex">Forex</SelectItem>
                  <SelectItem value="crypto">Crypto</SelectItem>
                  <SelectItem value="commodity">Commodity</SelectItem>
                  <SelectItem value="index">Index</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeframe">Timeframe</Label>
              <Select onValueChange={(value) => register("timeframe").onChange({ target: { value } })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select timeframe" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1m">1 Minute</SelectItem>
                  <SelectItem value="5m">5 Minutes</SelectItem>
                  <SelectItem value="15m">15 Minutes</SelectItem>
                  <SelectItem value="1h">1 Hour</SelectItem>
                  <SelectItem value="4h">4 Hours</SelectItem>
                  <SelectItem value="1d">1 Day</SelectItem>
                  <SelectItem value="1w">1 Week</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Indicators */}
          <div className="space-y-2">
            <Label htmlFor="indicators">Indicators (JSON format)</Label>
            <Textarea
              id="indicators"
              placeholder='{"ema": {"fast": 9, "slow": 20}, "rsi": {"period": 14, "overbought": 70, "oversold": 30}}'
              className="min-h-[120px] font-mono"
              {...register("indicators")}
            />
            <p className="text-sm text-gray-500">
              Optional: Provide indicators configuration in JSON format
            </p>
          </div>

          {/* Required Rules */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="entry_rules">
                Entry Rules <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="entry_rules"
                placeholder="Describe the conditions for entering a trade..."
                className="min-h-[120px]"
                {...register("entry_rules")}
              />
              {errors.entry_rules && (
                <p className="text-sm text-red-500">{errors.entry_rules.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="exit_rules">
                Exit Rules <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="exit_rules"
                placeholder="Describe the conditions for exiting a trade..."
                className="min-h-[120px]"
                {...register("exit_rules")}
              />
              {errors.exit_rules && (
                <p className="text-sm text-red-500">{errors.exit_rules.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="risk_rules">
                Risk Management Rules <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="risk_rules"
                placeholder="Describe your risk management approach (stop loss, position sizing, etc.)..."
                className="min-h-[120px]"
                {...register("risk_rules")}
              />
              {errors.risk_rules && (
                <p className="text-sm text-red-500">{errors.risk_rules.message}</p>
              )}
            </div>
          </div>

          {/* Additional Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Additional Notes</Label>
            <Textarea
              id="notes"
              placeholder="Any additional information or preferences..."
              className="min-h-[80px]"
              {...register("notes")}
            />
          </div>

          {/* Submit Button */}
          <div className="flex justify-end space-x-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => reset()}
              disabled={isSubmitting}
            >
              Reset
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Submit Request
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}