import { themes } from "@/registry/themes";
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function numberToCurrencyWords(amount: number): string {
  const ones = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
    'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
    'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'
  ];
  const tens = [
    '', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy',
    'Eighty', 'Ninety'
  ];

  const getWords = (n: number): string => {
    if (n < 20) return ones[n];
    if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 ? ' ' + ones[n % 10] : '');
    if (n < 1000) return ones[Math.floor(n / 100)] + ' Hundred' + (n % 100 ? ' ' + getWords(n % 100) : '');
    return '';
  };

  const num = Math.floor(amount); // integer part
  const paise = Math.round((amount - num) * 100); // two decimal places as paise

  if (num === 0 && paise === 0) {
    return 'Zero Rupees Only';
  }

  const crore = Math.floor(num / 10000000);
  const lakh = Math.floor((num % 10000000) / 100000);
  const thousand = Math.floor((num % 100000) / 1000);
  const hundred = Math.floor((num % 1000) / 100);
  const rest = num % 100;

  let result = 'Rupees ';
  if (crore) result += getWords(crore) + ' Crore ';
  if (lakh) result += getWords(lakh) + ' Lakh ';
  if (thousand) result += getWords(thousand) + ' Thousand ';
  if (hundred) result += getWords(hundred) + ' Hundred ';
  if (rest || (!crore && !lakh && !thousand && !hundred)) result += getWords(rest) + ' ';

  result = result.trim();
  if (paise > 0) {
    result += ' and ' + getWords(paise) + ' Paise';
  }

  result += ' Only';
  return result;
}



///
export function getImageUrl(path: string | null | undefined): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_SERVER || '';
  if (!path) return ''; // fallback for null/undefined paths
  return `${baseUrl}${path.startsWith('/') ? path : `/${path}}`}`;
  }



// 1. Helper: Convert HSL to RGB
function hslToRgb(h: number, s: number, l: number) {
  s /= 100;
  l /= 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  let r = 0, g = 0, b = 0;
  
  if (h < 60) {
    r = c; g = x; b = 0;
  } else if (h < 120) {
    r = x; g = c; b = 0;
  } else if (h < 180) {
    r = 0; g = c; b = x;
  } else if (h < 240) {
    r = 0; g = x; b = c;
  } else if (h < 300) {
    r = x; g = 0; b = c;
  } else {
    r = c; g = 0; b = x;
  }
  
  return {
    r: Math.round((r + m) * 255),
    g: Math.round((g + m) * 255),
    b: Math.round((b + m) * 255),
  };
}

// 2. Helper: Convert RGB to Hex
function rgbToHex(r: number, g: number, b: number): string {
  return "#" + [r, g, b]
    .map((x) => {
      const hex = x.toString(16);
      return hex.length === 1 ? "0" + hex : hex;
    })
    .join("");
}

// 3. Find theme by name and get its primary color in hex
export function getThemePrimaryHex(themeName: string, mode: "light" | "dark"): string | null {
  const theme = themes.find((t) => t.name === themeName);
  if (!theme) return null;

  const hslString = theme.cssVars[mode].primary; // e.g., "240 5.9% 10%"
  // Split the string and remove any "%" signs
  const [hStr, sStr, lStr] = hslString.split(" ");
  const h = parseFloat(hStr);
  const s = parseFloat(sStr.replace("%", ""));
  const l = parseFloat(lStr.replace("%", ""));

  const { r, g, b } = hslToRgb(h, s, l);
  return rgbToHex(r, g, b);
}


export const maskEmail = (email: string): string => {
  try
  {
    const [name, domain] = email.split("@");
    if (name.length <= 2) {
      return `${name[0]}*...@${domain}`; // Handle short names
    }
    return `${name.slice(0, 2)}***@${domain}`; // Mask part of the username
  }
  catch (e)
  {
    return email;
  }
  
};

export function numberToWords(amount: number): string {
  const ones = [
    '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
    'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
    'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'
  ];
  const tens = [
    '', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy',
    'Eighty', 'Ninety'
  ];

  const getWords = (n: number): string => {
    if (n < 20) return ones[n];
    if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 ? ' ' + ones[n % 10] : '');
    if (n < 1000) return ones[Math.floor(n / 100)] + ' Hundred' + (n % 100 ? ' ' + getWords(n % 100) : '');
    return '';
  };

  const num = Math.floor(amount); // integer part
  const paise = Math.round((amount - num) * 100); // two decimal places as paise

  const crore = Math.floor(num / 10000000);
  const lakh = Math.floor((num % 10000000) / 100000);
  const thousand = Math.floor((num % 100000) / 1000);
  const hundred = Math.floor((num % 1000) / 100);
  const rest = num % 100;

  let result = 'Rupees ';
  if (crore) result += getWords(crore) + ' Crore ';
  if (lakh) result += getWords(lakh) + ' Lakh ';
  if (thousand) result += getWords(thousand) + ' Thousand ';
  if (hundred) result += getWords(hundred) + ' Hundred ';
  if (rest || (!crore && !lakh && !thousand && !hundred)) result += getWords(rest) + ' ';

  result = result.trim();
  if (paise > 0) {
    result += ' and ' + getWords(paise) + ' Paise';
  }

  return result;
}