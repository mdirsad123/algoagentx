"use client";

import { useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalTitle,
  ModalClose,
} from "@/components/ui/Modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/components/shared/toast";
import { X } from "lucide-react";

interface RequestStrategyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

// Trading style options
const TRADING_STYLES = [
  { value: "intraday", label: "Intraday" },
  { value: "swing", label: "Swing" },
  { value: "scalping", label: "Scalping" },
  { value: "positional", label: "Positional" },
];

// Risk level options
const RISK_LEVELS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

// Timeframe options
const TIMEFRAMES = [
  { value: "1m", label: "1 Minute" },
  { value: "5m", label: "5 Minutes" },
  { value: "15m", label: "15 Minutes" },
  { value: "30m", label: "30 Minutes" },
  { value: "1h", label: "1 Hour" },
  { value: "4h", label: "4 Hours" },
  { value: "1D", label: "1 Day" },
  { value: "1W", label: "1 Week" },
  { value: "1M", label: "1 Month" },
];

// Instrument options
const INSTRUMENTS = [
  { value: "stocks", label: "Stocks" },
  { value: "options", label: "Options" },
  { value: "futures", label: "Futures" },
  { value: "crypto", label: "Crypto" },
  { value: "forex", label: "Forex" },
];

// Approach options (multi-select)
const APPROACHES = [
  { value: "indicator_based", label: "Indicator Based" },
  { value: "price_action", label: "Price Action" },
  { value: "smc", label: "SMC (Smart Money Concepts)" },
  { value: "ict", label: "ICT (Inner Circle Trader)" },
  { value: "news_based", label: "News Based" },
];

// Predefined indicator options
const INDICATOR_OPTIONS = [
  { value: "rsi", label: "RSI" },
  { value: "macd", label: "MACD" },
  { value: "ema", label: "EMA" },
  { value: "sma", label: "SMA" },
  { value: "vwap", label: "VWAP" },
  { value: "bollinger_bands", label: "Bollinger Bands" },
  { value: "atr", label: "ATR" },
  { value: "stochastic", label: "Stochastic" },
  { value: "fibonacci", label: "Fibonacci" },
  { value: "ichimoku", label: "Ichimoku" },
];

interface FormData {
  strategy_name: string;
  trading_style: string;
  risk_level: string;
  entry_logic: string;
  exit_logic: string;
  timeframe: string;
  instrument: string;
  approaches: string[];
  indicators: string[];
  custom_indicators: string;
  notes: string;
}

interface FormErrors {
  [key: string]: string;
}

export function RequestStrategyModal({
  isOpen,
  onClose,
  onSuccess,
}: RequestStrategyModalProps) {
  const { showToast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    strategy_name: "",
    trading_style: "",
    risk_level: "",
    entry_logic: "",
    exit_logic: "",
    timeframe: "",
    instrument: "",
    approaches: [],
    indicators: [],
    custom_indicators: "",
    notes: "",
  });
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user starts typing
    if (formErrors[name]) {
      setFormErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handleSelectChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (formErrors[name]) {
      setFormErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const handleApproachToggle = (approachValue: string) => {
    setFormData((prev) => ({
      ...prev,
      approaches: prev.approaches.includes(approachValue)
        ? prev.approaches.filter((a) => a !== approachValue)
        : [...prev.approaches, approachValue],
    }));
  };

  const handleIndicatorToggle = (indicatorValue: string) => {
    setFormData((prev) => ({
      ...prev,
      indicators: prev.indicators.includes(indicatorValue)
        ? prev.indicators.filter((i) => i !== indicatorValue)
        : [...prev.indicators, indicatorValue],
    }));
  };

  const validateForm = (): boolean => {
    const errors: FormErrors = {};

    if (!formData.strategy_name.trim()) {
      errors.strategy_name = "Strategy name is required";
    }
    if (!formData.trading_style) {
      errors.trading_style = "Trading style is required";
    }
    if (!formData.risk_level) {
      errors.risk_level = "Risk level is required";
    }
    if (!formData.entry_logic.trim()) {
      errors.entry_logic = "Entry logic is required";
    }
    if (!formData.exit_logic.trim()) {
      errors.exit_logic = "Exit logic is required";
    }
    if (!formData.timeframe) {
      errors.timeframe = "Timeframe is required";
    }
    if (!formData.instrument) {
      errors.instrument = "Instrument is required";
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Get auth token
      const token = localStorage.getItem("access_token");
      if (!token) {
        showToast("Please log in to submit a strategy request", "error");
        setIsSubmitting(false);
        return;
      }

      // Prepare payload for API
      const payload = {
        title: formData.strategy_name,
        strategy_type: formData.approaches.join(", "),
        market: formData.instrument,
        timeframe: formData.timeframe,
        indicators: {
          selected: formData.indicators,
          custom: formData.custom_indicators,
          approaches: formData.approaches,
        },
        entry_rules: formData.entry_logic,
        exit_rules: formData.exit_logic,
        risk_rules: `Risk Level: ${formData.risk_level}`,
        notes: formData.notes,
      };

      const response = await fetch("/api/v1/strategy-requests/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to submit strategy request");
      }

      // Success
      showToast("Strategy Request Submitted Successfully! Our team will review it shortly.", "success");

      // Reset form
      resetForm();

      // Close modal and trigger success callback
      onClose();
      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      showToast(
        error instanceof Error ? error.message : "An error occurred while submitting your request",
        "error"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      strategy_name: "",
      trading_style: "",
      risk_level: "",
      entry_logic: "",
      exit_logic: "",
      timeframe: "",
      instrument: "",
      approaches: [],
      indicators: [],
      custom_indicators: "",
      notes: "",
    });
    setFormErrors({});
  };

  const handleModalClose = () => {
    resetForm();
    onClose();
  };

  return (
    <Modal open={isOpen} onOpenChange={handleModalClose}>
        <ModalContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-gradient-to-br from-[#4f1d95]/95 via-[#341672]/95 to-[#1f2647]/95 backdrop-blur-xl border border-white/20 shadow-2xl shadow-purple-950/50">
        <ModalHeader className="border-b border-white/20 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <ModalTitle className="text-xl font-semibold bg-gradient-to-r from-white via-purple-200 to-purple-300 bg-clip-text text-transparent">
                Request Custom Strategy
              </ModalTitle>
              <p className="text-sm text-purple-100/80 mt-1">
                Fill out the form below to request a custom trading strategy
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-green-400/80 shadow-lg shadow-green-400/30"></div>
              <span className="text-xs text-purple-100/60">Live Support</span>
            </div>
          </div>
        </ModalHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-6 py-4">
            {/* Basic Info Section */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-purple-300 uppercase tracking-wider">
                Basic Information
              </h4>

              <div className="space-y-2">
                <label className="text-sm text-purple-200">
                  Strategy Name <span className="text-red-400">*</span>
                </label>
                <Input
                  name="strategy_name"
                  value={formData.strategy_name}
                  onChange={handleInputChange}
                  placeholder="e.g., My Awesome Momentum Strategy"
                  className={`bg-white/10 border-white/20 text-white placeholder:text-purple-100/50 focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30 ${
                    formErrors.strategy_name ? "border-red-400" : ""
                  }`}
                />
                {formErrors.strategy_name && (
                  <p className="text-xs text-red-400">{formErrors.strategy_name}</p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm text-purple-200">
                    Trading Style <span className="text-red-400">*</span>
                  </label>
                  <Select
                    value={formData.trading_style}
                    onValueChange={(value) =>
                      handleSelectChange("trading_style", value)
                    }
                  >
                    <SelectTrigger
                      className={`bg-white/10 border-white/20 text-white focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30 ${
                        formErrors.trading_style ? "border-red-400" : ""
                      }`}
                    >
                      <SelectValue placeholder="Select style" />
                    </SelectTrigger>
                    <SelectContent>
                      {TRADING_STYLES.map((style) => (
                        <SelectItem key={style.value} value={style.value}>
                          {style.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {formErrors.trading_style && (
                    <p className="text-xs text-red-400">
                      {formErrors.trading_style}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-purple-200">
                    Risk Level <span className="text-red-400">*</span>
                  </label>
                  <Select
                    value={formData.risk_level}
                    onValueChange={(value) =>
                      handleSelectChange("risk_level", value)
                    }
                  >
                    <SelectTrigger
                      className={`bg-white/10 border-white/20 text-white focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30 ${
                        formErrors.risk_level ? "border-red-400" : ""
                      }`}
                    >
                      <SelectValue placeholder="Select risk" />
                    </SelectTrigger>
                    <SelectContent>
                      {RISK_LEVELS.map((level) => (
                        <SelectItem key={level.value} value={level.value}>
                          {level.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {formErrors.risk_level && (
                    <p className="text-xs text-red-400">{formErrors.risk_level}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Trading Setup Section */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-purple-300 uppercase tracking-wider">
                Trading Setup
              </h4>

              <div className="space-y-2">
                <label className="text-sm text-purple-200">
                  Entry Logic <span className="text-red-400">*</span>
                </label>
                <Textarea
                  name="entry_logic"
                  value={formData.entry_logic}
                  onChange={handleInputChange}
                  placeholder="Describe your entry conditions (e.g., RSI crosses above 30, price above EMA 50, etc.)"
                  rows={4}
                  className={`bg-white/10 border-white/20 text-white placeholder:text-purple-100/50 focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30 ${
                    formErrors.entry_logic ? "border-red-400" : ""
                  }`}
                />
                {formErrors.entry_logic && (
                  <p className="text-xs text-red-400">{formErrors.entry_logic}</p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm text-purple-200">
                  Exit Logic <span className="text-red-400">*</span>
                </label>
                <Textarea
                  name="exit_logic"
                  value={formData.exit_logic}
                  onChange={handleInputChange}
                  placeholder="Describe your exit conditions (e.g., RSI crosses below 70, trailing stop loss, etc.)"
                  rows={4}
                  className={`bg-white/10 border-white/20 text-white placeholder:text-purple-100/50 focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30 ${
                    formErrors.exit_logic ? "border-red-400" : ""
                  }`}
                />
                {formErrors.exit_logic && (
                  <p className="text-xs text-red-400">{formErrors.exit_logic}</p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm text-purple-200">
                    Timeframe <span className="text-red-400">*</span>
                  </label>
                  <Select
                    value={formData.timeframe}
                    onValueChange={(value) =>
                      handleSelectChange("timeframe", value)
                    }
                  >
                    <SelectTrigger
                      className={`bg-white/10 border-white/20 text-white focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30 ${
                        formErrors.timeframe ? "border-red-400" : ""
                      }`}
                    >
                      <SelectValue placeholder="Select timeframe" />
                    </SelectTrigger>
                    <SelectContent>
                      {TIMEFRAMES.map((tf) => (
                        <SelectItem key={tf.value} value={tf.value}>
                          {tf.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {formErrors.timeframe && (
                    <p className="text-xs text-red-400">{formErrors.timeframe}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-purple-200">
                    Instrument <span className="text-red-400">*</span>
                  </label>
                  <Select
                    value={formData.instrument}
                    onValueChange={(value) =>
                      handleSelectChange("instrument", value)
                    }
                  >
                    <SelectTrigger
                      className={`bg-white/10 border-white/20 text-white focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30 ${
                        formErrors.instrument ? "border-red-400" : ""
                      }`}
                    >
                      <SelectValue placeholder="Select instrument" />
                    </SelectTrigger>
                    <SelectContent>
                      {INSTRUMENTS.map((inst) => (
                        <SelectItem key={inst.value} value={inst.value}>
                          {inst.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {formErrors.instrument && (
                    <p className="text-xs text-red-400">{formErrors.instrument}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Strategy Type Section */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-purple-300 uppercase tracking-wider">
                Strategy Approach
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {APPROACHES.map((approach) => (
                  <div
                    key={approach.value}
                    className="flex items-center space-x-3 p-3 rounded-lg bg-gradient-to-r from-white/10 to-purple-500/10 border border-white/20 hover:border-purple-400/50 transition-all duration-200 cursor-pointer hover:shadow-lg hover:shadow-purple-500/20"
                    onClick={() => handleApproachToggle(approach.value)}
                  >
                    <Checkbox
                      checked={formData.approaches.includes(approach.value)}
                      onCheckedChange={() => handleApproachToggle(approach.value)}
                      className="data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground"
                    />
                    <span className="text-sm text-purple-200">
                      {approach.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Indicators Section */}
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-purple-300 uppercase tracking-wider">
                Indicators
              </h4>
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Select the indicators you want to use:
                </p>
                <div className="flex flex-wrap gap-2">
                  {INDICATOR_OPTIONS.map((indicator) => (
                    <button
                      key={indicator.value}
                      type="button"
                      onClick={() => handleIndicatorToggle(indicator.value)}
                    className={`px-3 py-1.5 rounded-full text-sm transition-all duration-200 ${
                        formData.indicators.includes(indicator.value)
                          ? "bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/30"
                          : "bg-white/10 text-purple-100 border border-white/20 hover:border-purple-400/50 hover:bg-white/20"
                      }`}
                    >
                      {indicator.label}
                      {formData.indicators.includes(indicator.value) && (
                        <X className="inline-block ml-1 h-3 w-3" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-purple-200">
                  Custom Indicators
                </label>
                <Input
                  name="custom_indicators"
                  value={formData.custom_indicators}
                  onChange={handleInputChange}
                  placeholder="e.g., Supertrend, ADX (comma separated)"
                  className="bg-white/10 border-white/20 text-white placeholder:text-purple-100/50 focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30"
                />
              </div>
            </div>

            {/* Notes Section */}
            <div className="space-y-2">
              <label className="text-sm text-purple-200">
                Additional Notes / Special Requirements
              </label>
                <Textarea
                  name="notes"
                  value={formData.notes}
                  onChange={handleInputChange}
                  placeholder="Any additional details, special requirements, or specific preferences..."
                  rows={3}
                  className="bg-white/10 border-white/20 text-white placeholder:text-purple-100/50 focus:border-purple-400 focus:ring-2 focus:ring-purple-400/30"
                />
            </div>
          </div>

          <ModalFooter className="border-t border-white/20 pt-4 gap-3">
            <ModalClose asChild>
              <Button
                type="button"
                variant="outline"
                onClick={handleModalClose}
                className="border-white/20 text-purple-100 hover:bg-white/10 hover:border-purple-400/50 transition-all duration-200"
              >
                Cancel
              </Button>
            </ModalClose>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0 min-w-[140px] shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/40"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="animate-spin h-4 w-4"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Submitting...
                </span>
              ) : (
                "Submit Request"
              )}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
}