"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import PublicOnly from "@/components/auth/PublicOnly";
import Alert from "@/components/ui/Alert";
import { ROUTES } from "@/lib/constants/routes";
import { useAuth } from "@/lib/hooks/useAuth";
import { getApiErrorMessage } from "@/lib/utils/errors";

const INITIAL_FORM = {
  firstName: "",
  lastName: "",
  email: "",
  password: "",
  confirmPassword: "",
};

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [form, setForm] = useState(INITIAL_FORM);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleChange(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (form.password !== form.confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setSubmitting(true);

    try {
      await register({
        firstName: form.firstName,
        lastName: form.lastName,
        email: form.email,
        password: form.password,
      });
      router.replace(ROUTES.APP);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "No se pudo crear la cuenta."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PublicOnly>
      <main className="authPage">
        <section className="authPanel authIntro">
          <div className="brandMark brandMarkLarge">BI</div>
          <p className="eyebrow">NUEVO USUARIO</p>
          <h1>Crea tu acceso a la plataforma.</h1>
          <p>
            Al terminar el registro, el frontend inicia sesión automáticamente usando los endpoints JWT
            del backend.
          </p>
        </section>

        <section className="authPanel authFormPanel">
          <form className="authForm" onSubmit={handleSubmit}>
            <div>
              <p className="eyebrow">REGISTRO</p>
              <h2>Crear cuenta</h2>
              <p className="muted">La contraseña debe tener al menos 8 caracteres.</p>
            </div>

            <Alert>{error}</Alert>

            <div className="fieldGrid">
              <label className="field">
                <span>Nombres</span>
                <input name="firstName" onChange={handleChange} value={form.firstName} />
              </label>

              <label className="field">
                <span>Apellidos</span>
                <input name="lastName" onChange={handleChange} value={form.lastName} />
              </label>
            </div>

            <label className="field">
              <span>Correo electrónico</span>
              <input
                autoComplete="email"
                name="email"
                onChange={handleChange}
                required
                type="email"
                value={form.email}
              />
            </label>

            <label className="field">
              <span>Contraseña</span>
              <input
                autoComplete="new-password"
                minLength={8}
                name="password"
                onChange={handleChange}
                required
                type="password"
                value={form.password}
              />
            </label>

            <label className="field">
              <span>Confirmar contraseña</span>
              <input
                autoComplete="new-password"
                minLength={8}
                name="confirmPassword"
                onChange={handleChange}
                required
                type="password"
                value={form.confirmPassword}
              />
            </label>

            <button className="button buttonPrimary buttonBlock" disabled={submitting} type="submit">
              {submitting ? "Creando cuenta..." : "Crear cuenta"}
            </button>

            <p className="authFooterText">
              ¿Ya tienes una cuenta? <Link href={ROUTES.LOGIN}>Iniciar sesión</Link>
            </p>
          </form>
        </section>
      </main>
    </PublicOnly>
  );
}
