// import styles from "./index.module.scss";
import LoginForm from "./LoginForm/index.tsx";
import LoginBackground from "./LoginBackground";

const LoginBoxView: React.FC = () => {
  return (
    <div style={{ position: "relative" }}>
      <LoginBackground />

      <LoginForm />
    </div>
  );
};

export default LoginBoxView;
