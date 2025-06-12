import SignInButton from "@/components/ui/SignInButton";

const LoginPage: React.FC = () => {
  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h1>Login to Your SaaS</h1>
      <p>Choose your preferred authentication method:</p>
      <SignInButton />
    </div>
  );
};

export default LoginPage;