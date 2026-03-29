
import CryptoJS from "crypto-js";

const secret_key=process.env.NEXT_PUBLIC_SECRET_KEY || "secret_key";

const encrypt = (data: any) => {
  return CryptoJS.AES.encrypt(JSON.stringify(data), secret_key).toString();
};

const decrypt = (cipherText: string) => {
  try {
    const bytes = CryptoJS.AES.decrypt(cipherText, secret_key);
    return JSON.parse(bytes.toString(CryptoJS.enc.Utf8));
  } catch (error) {
    console.error("Decryption failed:", error);
    return null;
  }
};

// Custom storage handler with encryption
export const secureStorage = {
    getItem: (key: string) => {
      const encryptedData = localStorage.getItem(key);
      return encryptedData ? decrypt(encryptedData) : null;
    },
    setItem: (key: string, newValue: any) => {
      if (newValue === null) {
        localStorage.removeItem(key); // Remove key instead of storing "null"
      } else {
        localStorage.setItem(key, encrypt(newValue));
      }
    },
    removeItem: (key: string) => {
      localStorage.removeItem(key);
    },
  };


