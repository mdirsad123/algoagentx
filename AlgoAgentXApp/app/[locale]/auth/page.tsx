"use client"
import React, { useState } from 'react'
import LoginForm from './components/login-form';
import CompanyRegistrationTab from './registration/page';

export default function Page() {
  const [showRegister, setShowRegister] = useState(false);

  return (
    <div>
      <div>
          <div>
            <LoginForm />
          </div>
      </div>
    </div>
  );
}
