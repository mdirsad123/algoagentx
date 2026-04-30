// Global type declarations for external libraries
/// <reference types="js-cookie" />

// Declare module for js-cookie if needed
declare module 'js-cookie' {
  interface CookieAttributes {
    path?: string;
    domain?: string;
    expires?: number | Date;
    secure?: boolean;
    sameSite?: 'strict' | 'lax' | 'none';
  }

  interface CookiesStatic {
    get(key: string): string | undefined;
    get(): { [key: string]: string };
    set(key: string, value: string, attributes?: CookieAttributes): void;
    remove(key: string, attributes?: CookieAttributes): void;
  }

  const Cookies: CookiesStatic;
  export default Cookies;
}