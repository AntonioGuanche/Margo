import { useParams } from 'react-router-dom';
import RecipeForm from '../components/RecipeForm';

export default function RecipeEdit() {
  const { id } = useParams<{ id: string }>();
  return <RecipeForm recipeId={id ? parseInt(id) : undefined} />;
}
