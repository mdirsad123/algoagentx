import React, { useState, useContext } from "react";
import axiosInstance from "@/lib/axios";
import { useQueryClient, useQuery, useMutation } from "@tanstack/react-query";

export const useFetcher = (
  url: string,
  key: string,
  enabled: boolean = true
) => {
  const queryClient = useQueryClient();
  const [pageReset, setPageReset] = useState(false);
  const apiURL = process.env.REACT_APP_API_SERVER;
  const fetchData = async () => {
    const response = await axiosInstance.get(url);
    return response.data;
  };

  const { data, isLoading, isError, error, isSuccess, isFetching, refetch } =
    useQuery({ queryKey: [key], enabled, staleTime: 1, queryFn: fetchData });

  return { data, isLoading, isError, error, isSuccess, isFetching, refetch };
};

export const useFetcherWithPost = (
  url: string,
  key: string,
  userData: any,
  enabled = true
) => {
  const queryClient = useQueryClient();
  const [pageReset, setPageReset] = useState(false);

  const fetchData = async (userData: any) => {
    axiosInstance.defaults.headers["Content-Type"] = "application/json";
    const { data } = await axiosInstance.post(url, JSON.stringify(userData));
    return data;
  };

  const { data, isLoading, isError, error, isSuccess, isFetching, refetch } =
    useQuery({
      queryKey: [key],
      enabled,
      staleTime: 1,
      queryFn: () => fetchData(userData),
    });

  return { data, isLoading, isError, error, isSuccess, isFetching, refetch };
};

export const usePoster = (
  url: string,
  key: string,
  onSuccess: any,
  onError: any
) => {
  //   const toast = useToast();
  const queryClient = useQueryClient();

  const title = key;
  const postData = async (userData: any) => {
    console.log(userData);
    axiosInstance.defaults.headers["Content-Type"] = "application/json";
    const { data } = await axiosInstance.post(url, JSON.stringify(userData));
    return data;
  };

  const {
    mutate,
    data,
    isPending: isLoading,
    isError,
    isSuccess,
    status,
  } = useMutation({
    mutationFn: postData,
    onSuccess: (response) => {
      console.log("success");
      queryClient.invalidateQueries({ queryKey: [key] });
      if (onSuccess) {
        onSuccess(response);
      }
    },
    onError: (error:Error) => {
      console.log(error.message);
      
      if (onError) {
        onError(error);
      }
    },
  });

  return { mutate, data, isLoading, isError, isSuccess, status };
};

export const usePosterWithFileUpload = (
  url: string,
  key: string,
  onSuccess?: (data: any) => void,
  onError?: (error: any) => void,
  method: 'POST' | 'PUT' = 'POST' // 5th argument with default
) => {
  const queryClient = useQueryClient();

  const postData = async (formData: FormData) => {
    const { data } = await axiosInstance.request({
      url,
      method,
      data: formData,
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return data;
  };

  const {
    mutate,
    data,
    isPending: isLoading,
    isError,
    isSuccess,
    status,
  } = useMutation({
    mutationFn: postData,
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: [key] });
      if (onSuccess) onSuccess(response);
    },
    onError: (error) => {
      console.error("Upload error:", error);
      if (onError) onError(error);
    },
  });

  return { mutate, data, isLoading, isError, isSuccess, status };
};

export const useUpdater = (url:string, key:string, onSuccess:any, onError:any) => {
  const queryClient = useQueryClient();
  
  
  const title = key;

  const updateData = async (userData:any) => {
    console.log(userData);
    axiosInstance.defaults.headers["Content-Type"] = "application/json";
    const { data } = await axiosInstance.put(
      `${url}/`,
      JSON.stringify(userData)
    );
    return data;
  };

  const { mutate, data, isPending:isLoading, isError, isSuccess, status } = useMutation(
    {mutationFn: updateData,
    
      onSuccess: (response) => {
        console.log("success");
        queryClient.invalidateQueries({queryKey: [key]});
        if (onSuccess) {
          onSuccess(response);
        } 
      },
      onError: (error:Error) => {
        console.log(error.message);
        
        if (onError) {
          onError(error);
        } 
      },
    }
  );
  return { mutate, data, isLoading, isError, isSuccess, status };
};

export const usePatcher = (url:string, key:string, onSuccess:any, onError:any) => {
  const queryClient = useQueryClient();
  
  
  const title = key;

  const updateData = async (userData:any) => {
    console.log(userData);
    axiosInstance.defaults.headers["Content-Type"] = "application/json";
    const { data } = await axiosInstance.patch(
      `${url}/`,
      JSON.stringify(userData)
    );
    return data;
  };

  const { mutate, data, isPending:isLoading, isError, isSuccess, status } = useMutation(
    {mutationFn: updateData,
    
      onSuccess: (response) => {
        console.log("success");
        queryClient.invalidateQueries({queryKey: [key]});
        if (onSuccess) {
          onSuccess(response);
        } 
      },
      onError: (error:Error) => {
        console.log(error.message);
        
        if (onError) {
          onError(error);
        } 
      },
    }
  );
  return { mutate, data, isLoading, isError, isSuccess, status };
};

export const useUpdaterWithFileUpload = (url:string, key:string, onSuccess:any, onError:any) => {
  const queryClient = useQueryClient();
  
  
  const title = key;

  const updateData = async (userData:any) => {
    console.log('userData',userData.get("id"));

    axiosInstance.defaults.headers["Content-Type"] =
      "multipart/form-data; boundary=63c5979328c44e2c869349443a94200e";
    const { data } = await axiosInstance.put(
      url,
      userData
    );
    return data;
  };

  const { mutate, data, isPending:isLoading, isError, isSuccess, status } = useMutation(
    {mutationFn: updateData,
    
      onSuccess: (response) => {
        console.log("success");
        queryClient.invalidateQueries({queryKey:[key]});
        if (onSuccess) {
          onSuccess(response);
        } 
      },
      onError: (error) => {
        console.log(error.message);
        
        if (onError) {
          onError(error);
        }
      },
    }
  );
  return { mutate, data, isLoading, isError, isSuccess, status };
};


export const useDeleter = (url: string, key: string, onSuccess: any, onError: any) => {
  const queryClient = useQueryClient();
  
  const title = key;

  const deleteData = async (userData: any) => {
    console.log(userData);

    // FIXED THIS LINE 👇
    const { data } = await axiosInstance.patch(
  `${url}${userData}/`
);

    return data;
  };

  const { mutate, data } = useMutation({
    mutationFn: deleteData,
    onSuccess: (response) => {
      console.log("deleted successfully");
      queryClient.invalidateQueries({ queryKey: [key] });
      if (onSuccess) {
        onSuccess(response);
      }
    },
    onError: (error: Error) => {
      console.log(error.message);
      if (onError) {
        onError(error);
      }
    },
  });

  return { mutate, data };
};

export const useLocalStorage = (key:string, initialValue:any) => {
  
  const [tmpValue, setTmpValue] = useState();

  // State to store our value
  // Pass initial state function to useState so logic is only executed once
  const [storedValue, setStoredValue] = useState(() => {
    if (typeof window === "undefined") {
      setTmpValue(initialValue);
      return initialValue;
    }
    try {
      // Get from local storage by key
      const item = window.sessionStorage.getItem(key);
      var jitem = item ? JSON.parse(item) : null;
      // var decrypted = encryptor.decrypt(jitem);
      setTmpValue(jitem ? jitem : initialValue);
      // Parse stored json or if none return initialValue
      return jitem ? jitem : initialValue;
    } catch (error) {
      // If error also return initialValue
      console.log(error);
      setTmpValue(initialValue);
      return initialValue;
    }
  });
  // Return a wrapped version of useState's setter function that ...
  // ... persists the new value to localStorage.
  const setValue = (value:any) => {
    try {
      setTmpValue(value);
      // Allow value to be a function so we have same API as useState
      const valueToStore =
        value instanceof Function ? value(storedValue) : value;
      // Save state
      // var encrypted = encryptor.encrypt(valueToStore);
      setStoredValue(valueToStore);
      // Save to local storage
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      // A more advanced implementation would handle the error case
      console.log(error);
    }
  };
  return [tmpValue, setValue];
};
